import shutil
from datetime import timedelta
from pathlib import Path
from sqlalchemy.orm import Session, joinedload

from .logger_utils import LoggingAgent
from ..repository.models import File, BackupFile
from ..repository.database import BaseSQLAgent
from .config_utils import BackupConfig
from .time_utils import get_current_time


class BackupSchedulerAgent:
    def __init__(self, session_local, logger):
        self.SessionLocal = session_local
        self.logger = logger

    def _fetch_files_to_backup(self, session: Session):
        return (
            session.query(File)
            .filter(File.status == "uploaded")
            .filter(
                ~File.backups.any(
                    BackupFile.status.in_(
                        ["wait-for-backup", "backup-in-progress", "backed-up"]
                    )
                )
            )
            .all()
        )

    def schedule_new_backups(self):
        """Scan for new files that need backup and create backup records."""
        try:
            with self.SessionLocal() as session:
                try:
                    files_to_backup = self._fetch_files_to_backup(session)

                    if not files_to_backup:
                        self.logger.info("No new files to schedule for backup.")
                        return

                    for file in files_to_backup:
                        backup = BackupFile(file_id=file.id, status="wait-for-backup")
                        session.add(backup)

                    session.commit()
                    self.logger.info(
                        f"Scheduled {len(files_to_backup)} new files for backup"
                    )

                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Error scheduling backups: {e}")

        except Exception as db_error:
            self.logger.critical(f"Database session error: {db_error}")


class BackupProcessorAgent:
    def __init__(self, session_local, logger, source_root, backup_root, source_doc_dir):
        self.SessionLocal = session_local
        self.logger = logger
        self.source_root = Path(source_root).resolve()
        self.backup_root = Path(backup_root).resolve()
        self.source_doc_dir = Path(source_doc_dir).resolve()

    def _fetch_pending_backups(self, session: Session):
        """Fetch all backups that are pending."""
        return (
            session.query(BackupFile)
            .filter(BackupFile.status == "wait-for-backup")
            .options(joinedload(BackupFile.file))
            .all()
        )

    def _process_single_backup(self, session: Session, backup: BackupFile):
        """Process a single backup file."""
        try:
            backup.status = "backup-in-progress"
            backup.backup_started_at = get_current_time()
            session.commit()

            # Extract file details
            file: File = backup.file
            index_name = file.index_name
            file_dir_name = file.file_dir_name
            file_name = file.name
            process_type = file.process_type

            source_path = (self.source_root / file_dir_name).resolve(strict=False)
            backup_index_dir = (self.backup_root / index_name).resolve(strict=False)
            backup_index_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_index_dir / file_dir_name

            if source_path.is_dir():
                shutil.copytree(source_path, backup_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, backup_path)

            # Handle optional source document backup
            source_document = (
                self.source_doc_dir / index_name / process_type / "done" / file_name
            )
            if source_document.exists():
                shutil.copy2(source_document, backup_path)

            backup.status = "backed-up"
            backup.backup_path = str(backup_path)
            backup.backup_finished_at = get_current_time()

        except Exception as e:
            self.logger.error(f"Backup failed for file {backup.file_id}: {e}")
            backup.status = "backup-failed"

        finally:
            backup.last_change_at = get_current_time()
            session.commit()

    def process_pending_backups(self):
        """Process all files waiting for backup."""
        try:
            with self.SessionLocal() as session:
                pending_backups = self._fetch_pending_backups(session)

                if not pending_backups:
                    self.logger.info("No pending backups to process.")
                    return

                self.logger.info(f"Processing {len(pending_backups)} pending backups.")

                for backup in pending_backups:
                    self._process_single_backup(session, backup)

        except Exception as e:
            self.logger.critical(f"Error processing backups: {e}", exc_info=True)


class BackupRetentionAgent:
    def __init__(self, session_local, logger):
        self.SessionLocal = session_local
        self.logger = logger

    def mark_for_deletion(
        self,
        retention_days: int,
        retention_hours: int,
        retention_minutes: int,
        retention_seconds: int,
    ):
        """Mark backed-up files for deletion if original is no longer uploaded."""
        cutoff_date = get_current_time() - timedelta(
            days=retention_days,
            hours=retention_hours,
            minutes=retention_minutes,
            seconds=retention_seconds,
        )

        try:
            with self.SessionLocal() as session:
                backups_to_delete = (
                    session.query(BackupFile)
                    .join(File)
                    .filter(
                        BackupFile.status == "backed-up",
                        BackupFile.backup_finished_at <= cutoff_date,
                        File.status != "uploaded",
                    )
                    .all()
                )

                for backup in backups_to_delete:
                    backup.status = "wait-for-delete"
                    backup.last_change_at = get_current_time()

                session.commit()
                self.logger.info(
                    f"Marked {len(backups_to_delete)} backups for deletion"
                )

        except Exception as e:
            self.logger.error(f"Error marking backups for deletion: {e}")


class BackupDeletionAgent:
    def __init__(self, session_local, logger):
        self.SessionLocal = session_local
        self.logger = logger

    def process_deletions(self):
        """Process all files marked for deletion and update their status in the database."""
        try:
            with self.SessionLocal() as session:
                pending_deletions = (
                    session.query(BackupFile)
                    .filter(BackupFile.status == "wait-for-delete")
                    .all()
                )

                if not pending_deletions:
                    self.logger.info("No pending deletions found.")
                    return

                for backup in pending_deletions:
                    self._delete_backup_file(backup)

                session.commit()  # Commit once after processing all deletions

        except Exception as db_error:
            self.logger.critical(f"Database session error: {db_error}", exc_info=True)

    def _delete_backup_file(self, backup):
        """Attempts to delete a backup file or directory, logging any errors."""
        try:
            backup_path = Path(backup.backup_path).resolve(strict=False)

            if backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(backup_path)
                else:
                    backup_path.unlink()

            backup.status = "deleted"

        except Exception as e:
            self.logger.error(f"Deletion failed for backup {backup.id}: {e}")
            backup.status = "delete-failed"

        finally:
            backup.last_change_at = get_current_time()


class BackupManager:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.logger = LoggingAgent("Backup").logger
        self.SessionLocal = sql_agent.SessionLocal

        self.backup_config = BackupConfig()
        self.source_root = self.backup_config.source_root
        self.source_doc_dir = self.backup_config.source_doc_dir
        self.backup_root = self.backup_config.backup_root
        self.retention_days = self.backup_config.retention_days
        self.retention_hours = self.backup_config.retention_hours
        self.retention_minutes = self.backup_config.retention_minutes
        self.retention_seconds = self.backup_config.retention_seconds

        # Initialize agents
        self.scheduler_agent = BackupSchedulerAgent(self.SessionLocal, self.logger)
        self.processor_agent = BackupProcessorAgent(
            self.SessionLocal,
            self.logger,
            self.source_root,
            self.backup_root,
            self.source_doc_dir,
        )
        self.retention_agent = BackupRetentionAgent(self.SessionLocal, self.logger)
        self.deletion_agent = BackupDeletionAgent(self.SessionLocal, self.logger)

    def schedule_new_backups(self):
        """
        Schedule new backups for files that have not been backed up yet.
        """
        self.scheduler_agent.schedule_new_backups()

    def process_pending_backups(self):
        """
        Process all pending backups.
        """
        self.processor_agent.process_pending_backups()

    def mark_for_deletion(self):
        """
        Mark backups for deletion if original file is no longer uploaded.
        Retention period is set in days. Default is 14 days.
        """
        self.retention_agent.mark_for_deletion(
            self.retention_days,
            self.retention_hours,
            self.retention_minutes,
            self.retention_seconds,
        )

    def process_deletions(self):
        """
        Process all files marked for deletion.
        """
        self.deletion_agent.process_deletions()
