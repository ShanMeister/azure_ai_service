import shutil
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from .db_utils.models import File, SplitFile, Chunk
from .db_utils.database import BaseSQLAgent
from .logger_utils import LoggingAgent
from .config_utils import PathConfig


class DeleteFileError(Exception):
    pass


class DeleteSplitFileError(Exception):
    pass


class ScanDeleteAgent:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.SessionLocal = sql_agent.SessionLocal
        self.logger = LoggingAgent("DeleteAgent").logger
        self._path_config = PathConfig()

    def scan_wait_for_delete(self):
        """
        Scan files with specific statuses and mark them for deletion
        Criteria: Files with statuses 'wait-for-process', 'upload-failed', 'failed', 'uploaded', 'delete-failed' not in 'done' directory
        """
        self.logger.info("ScanDeleteAgent started scanning and labeling files.")
        with self.SessionLocal() as session:
            files_to_scan = self._fetch_files_to_scan(session)
            files_to_delete = [
                file for file in files_to_scan if not self._file_still_in_done_dir(file)
            ]
            if files_to_delete:
                self._bulk_update_file_status(
                    session, files_to_delete, "wait-for-delete"
                )
        self.logger.info("ScanDeleteAgent finished scanning and labeling files.")

    def _file_still_in_done_dir(self, file: File) -> bool:
        done_dir = self._path_config.get_done_dir(file.index_name, file.process_type)
        return (done_dir / file.name).exists()

    def _fetch_files_to_scan(self, session: Session) -> list[File]:
        """
        Fetch files with specific statuses.
        """
        return (
            session.query(File)
            .filter(
                File.status.in_(
                    [
                        "wait-for-process",
                        "upload-failed",
                        "failed",
                        "uploaded",
                        "delete-failed",
                    ]
                )
            )
            .all()
        )

    def _bulk_update_file_status(
        self, session: Session, files: list[File], status: str
    ) -> None:
        for file in files:
            file.status = status
        session.commit()
        self.logger.info(f"Updated status of {len(files)} files to {status}.")


class ScanDuplicateAgent:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.SessionLocal = sql_agent.SessionLocal
        self.logger = LoggingAgent("DeleteAgent").logger
        self._path_config = PathConfig()
        self.index_list = self._path_config.index_list

    def scan_exists_in_both_wait_done(self):
        """
        Scan files exists simultaneously in 'wait' and 'done' directories
        """
        with self.SessionLocal() as session:
            for index in self.index_list:
                for process_type in ["text", "text_image"]:
                    self._process_directory(session, index, process_type)

    def _process_directory(
        self, session: Session, index: str, process_type: str
    ) -> None:
        """
        Process all files in the given directory.

        :param session: Database session.
        :param index: Index of the directory.
        :param process_type: Type of processing ('text' or 'text_image').
        """
        try:
            self.logger.info(
                f"Scanning directory for (index={index}, process_type={process_type})"
            )
            wait_dir = self._path_config.get_wait_dir(index, process_type)
            done_dir = self._path_config.get_done_dir(index, process_type)

            pdf_files_wait_dir = self._get_all_pdf_paths(wait_dir)
            pdf_files_done_dir = self._get_all_pdf_paths(done_dir)
            pdf_names_wait_set = {pdf.name for pdf in pdf_files_wait_dir}

            for pdf_file_done in pdf_files_done_dir:
                if pdf_file_done.name in pdf_names_wait_set:
                    self._process_duplicate_file(session, pdf_file_done)
        except Exception as e:
            self.logger.error(f"Error processing directory: {e}")

    def _process_duplicate_file(self, session: Session, pdf_file_in_done_dir: Path):
        """
        Process a duplicate file found in the 'done' directory.

        :param session: Database session.
        :param pdf_file_in_done_dir: Path to the duplicate file in the 'done' directory.
        """
        try:
            files = (
                session.query(File)
                .filter(
                    File.name == pdf_file_in_done_dir.name, File.status != "deleted"
                )
                .all()
            )

            for file in files:
                file.status = "wait-for-delete"
                self.logger.info(
                    f"(file_id={file.id}, file_name={file.name}) is found existing in both 'wait' and 'done' dirs. Updated status to 'wait-for-delete'."
                )

            session.commit()
            pdf_file_in_done_dir.unlink()
            self.logger.info(
                f"Deleted file {pdf_file_in_done_dir.name} from 'done' directory."
            )
        except Exception as e:
            self.logger.error(f"Error processing duplicate file: {e}")

    def _get_all_pdf_paths(self, dir: Path) -> list[Path]:
        """
        Get all PDF file paths in a directory.

        :param dir: Directory to scan for PDF files.
        :return: List of paths to PDF files.
        """
        try:
            return list(dir.rglob("*.pdf"))
        except Exception as e:
            self.logger.error(f"Error accessing directory {dir}: {e}")
            return []


class LabelChunksDeleteAgent:

    def __init__(self, sql_agent: BaseSQLAgent) -> None:
        self.logger = LoggingAgent("DeleteAgent").logger
        self.SessionLocal = sql_agent.SessionLocal

    def label_chunks_for_delete(self):
        """
        Label chunks for deletion based on the status of their parent files.
        """
        with self.SessionLocal() as session:
            try:
                chunks = self._fetch_chunks_to_label(session)
                if chunks:
                    for chunk in chunks:
                        chunk.status = "wait-for-delete"
                    session.commit()
                    self.logger.info(
                        f"Updated status of {len(chunks)} chunks to 'wait-for-delete'."
                    )
                else:
                    self.logger.info("No chunks found to update.")
            except Exception as e:
                session.rollback()
                self.logger.exception("Error updating chunk status.", exc_info=e)

    def _fetch_chunks_to_label(self, session: Session) -> list[Chunk]:
        """
        Fetch chunks that need to be labeled for deletion.
        """
        return (
            session.query(Chunk)
            .join(SplitFile, SplitFile.id == Chunk.split_file_id)
            .join(File, File.id == SplitFile.file_id)
            .filter(File.status == "wait-for-delete")
            .all()
        )


class DeleteFilesAgent:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.logger = LoggingAgent("DeleteAgent").logger
        self.SessionLocal = sql_agent.SessionLocal
        self._path_config = PathConfig()

    def delete_files(self):
        self.logger.info("Start to delete all files.")
        with self.SessionLocal() as session:
            files = self._fetch_files_to_delete(session)
            if not files:
                self.logger.info("No files found to be deleted.")
                return

            for file in files:
                self._process_file_deletion(session, file)

    def _process_file_deletion(self, session: Session, file: File):
        try:
            if self._delete_splitfiles_sql_records(session, file):
                self._delete_folder(file)
                self._update_file_status(session, file, "deleted")
            else:
                self._update_file_status(session, file, "delete-failed")
        except Exception as e:
            self.logger.error(f"Error deleting file(id={file.id}): {e}")
            self._update_file_status(session, file, "delete-failed")

    def _delete_splitfiles_sql_records(self, session: Session, file: File) -> bool:
        for split_file in file.split_files:
            try:
                self._check_all_deleted_from_ai_search(session, split_file)
                self._delete_split_file_sql_record(session, split_file)
            except Exception as e:
                self.logger.error(f"Error deleting SplitFile(id={split_file.id}): {e}")
                return False
        return True

    def _update_file_status(self, session: Session, file: File, status: str):
        try:
            file.status = status
            session.commit()
            self.logger.info(f"File(id={file.id}) status updated to {status}.")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating file(id={file.id}) status: {e}")

    def _delete_split_file_sql_record(self, session: Session, split_file: SplitFile):
        try:
            session.delete(split_file)
            session.commit()
        except Exception as e:
            session.rollback()
            raise DeleteFileError(f"Error deleting SplitFile(id={split_file.id}): {e}")

    def _delete_folder(self, file: File):
        folder = self._path_config.meta_data_dir_path / file.file_dir_name
        if not folder.exists() or not folder.is_dir():
            self.logger.error(f"Invalid folder path: {folder}")
            return
        try:
            shutil.rmtree(folder)
            self.logger.info(f"Deleted folder: {folder}")
        except Exception as e:
            self.logger.error(f"Error deleting folder {folder}: {e}")

    def _fetch_files_to_delete(self, session: Session) -> list[File]:
        """
        Fetch files with status "wait-for-delete", including their split_files.
        """
        return (
            session.query(File)
            .filter_by(status="wait-for-delete")
            .options(
                joinedload(File.split_files)
            )  # Preload the split_files relationship
            .all()
        )

    def _check_all_deleted_from_ai_search(
        self, session: Session, split_file: SplitFile
    ):
        """
        Check if all chunks are deleted from AI search.
        """
        chunks = session.query(Chunk).filter_by(split_file_id=split_file.id).all()
        deleted_chunks = (
            session.query(Chunk)
            .filter_by(split_file_id=split_file.id, status="deleted")
            .all()
        )
        if len(chunks) != len(deleted_chunks):
            raise DeleteSplitFileError(
                f"Not all chunks deleted for SplitFile(id={split_file.id})."
            )
        self.logger.info(f"All chunks deleted for SplitFile(id={split_file.id}).")
