from pathlib import Path

from sqlalchemy.orm import Session, joinedload
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .db_utils.database import BaseSQLAgent
from .db_utils.models import SplitFile, Page, Chunk
from .logger_utils import LoggingAgent
from .config_utils import PathConfig, ChunkingConfig, TiktokenConfig
from .page_split import get_file_path

TiktokenConfig().set_tiktoken_cache_dir_in_env("o200k_base")


class ChunkGenerator:
    def __init__(self, sql_agent: BaseSQLAgent) -> None:
        self.logger = LoggingAgent("ChunkGenerator").logger
        self.SessionLocal = sql_agent.SessionLocal
        self.text_splitter = self._get_text_splitter()
        self.path_config = PathConfig()

    def generate(self):
        with self.SessionLocal() as session:
            splitfiles = self._fetch_splitfiles_to_process(session)
            if not splitfiles:
                self.logger.info("No unprocessed splitfiles found. Exit.")
                return

            self.logger.info(
                f"Found {len(splitfiles)} unprocessed splitfiles. Start chunking."
            )

            # Process splitfiles in a batch
            for splitfile in splitfiles:
                self._process_single_splitfile(session, splitfile)

    def _process_single_splitfile(self, session: Session, splitfile: SplitFile) -> None:
        try:
            self.logger.debug(f"Chunking splitfile {splitfile.id}.")
            # Generate chunks
            chunks = self._get_chunks(splitfile)

            # Bulk save chunks
            chunk_objects = [
                Chunk(content=chunk, split_file_id=splitfile.id) for chunk in chunks
            ]
            session.bulk_save_objects(chunk_objects)
            self._update_split_file_status(session, splitfile, "chunk-success")
            self.logger.info(f"Splitfile {splitfile.id} is chunked successfully.")

        except Exception as e:
            self.logger.error(f"Error processing split file ID {splitfile.id}: {e}")
            self._handle_processing_failure(session, splitfile, "chunk-failed")

    def _get_chunks(self, splitfile: SplitFile) -> list[str]:
        pages = self._get_sorted_pages(splitfile.pages)
        full_text = self._get_full_text(splitfile.file.file_dir_name, pages)
        return self.text_splitter.split_text(full_text)

    def _fetch_splitfiles_to_process(self, session: Session) -> list[SplitFile]:
        # Use lazy loading and filter out unnecessary data to optimize performance
        return (
            session.query(SplitFile)
            .filter(SplitFile.status == "bundle-success")
            .options(joinedload(SplitFile.file), joinedload(SplitFile.pages))
            .all()
        )

    def _get_full_text(self, file_dir_name: str, pages: list[Page]) -> str:
        # Use generator expression to avoid string concatenation overhead
        return "".join(
            self._read_bundle_md(file_dir_name, page.page_number) for page in pages
        )

    def _read_bundle_md(self, file_dir_name: str, page_number: int) -> str:
        # Helper to read markdown files
        bundle_md_path = self._get_bundle_md_path(file_dir_name, page_number)
        try:
            with open(bundle_md_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.warning(f"File not found: {bundle_md_path}")
            return ""

    def _get_bundle_md_path(self, file_dir_name: str, page_number: int) -> Path:
        return get_file_path(
            self.path_config.get_bundle_md_dir_path(file_dir_name),
            page_number,
            extension=".md",
        )

    def _get_sorted_pages(self, pages: list[Page]) -> list[Page]:
        return sorted(pages, key=lambda p: p.page_number)

    def _get_text_splitter(self) -> RecursiveCharacterTextSplitter:
        # Configuration is initialized once
        config = ChunkingConfig()
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name=config.model_name,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    def _update_split_file_status(
        self, session: Session, split_file: SplitFile, status: str
    ):
        """
        Updates the status of a split file in the database.
        """
        split_file.status = status
        session.commit()

    def _handle_processing_failure(
        self, session: Session, split_file: SplitFile, error_status: str
    ):
        """
        Handles processing failures by rolling back and updating the status.
        """
        session.rollback()
        self._update_split_file_status(session, split_file, error_status)
