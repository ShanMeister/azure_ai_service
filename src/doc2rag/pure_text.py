from pathlib import Path

from sqlalchemy.orm import Session, joinedload
import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .db_utils.database import BaseSQLAgent
from .logger_utils import LoggingAgent
from .db_utils.models import SplitFile, Chunk
from .config_utils import PathConfig, ChunkingConfig, TiktokenConfig

TiktokenConfig().set_tiktoken_cache_dir_in_env("o200k_base")


class PureTextFileProcessor:
    def __init__(self, sql_agent: BaseSQLAgent):
        self.logger = LoggingAgent("PureTextFileProcessor").logger
        self.SessionLocal = sql_agent.SessionLocal
        self.text_splitter = self._get_text_splitter()
        self.path_config = PathConfig()

    def convert2markdown_and_chunking(self):
        """
        Main function to process files: converts to Markdown and chunks the text.
        """
        with self.SessionLocal() as session:
            split_files = self._fetch_split_files_to_analyze(session)
            if not split_files:
                self.logger.info("No split files found for processing.")
                return

            for split_file in split_files:
                self._process_split_file(session, split_file)

    def _process_split_file(self, session: Session, split_file: SplitFile) -> None:
        """
        Processes a single split file: validates, converts, chunks, and updates status.
        """
        try:
            self.logger.info(f"Processing split file ID {split_file.id}.")
            split_file_path = self._get_file_path_and_validate(split_file)

            # Convert to Markdown and chunk the text
            full_text = self.extract_markdown_with_metadata(
                split_file_path, split_file.file.name
            )
            chunks = self.text_splitter.split_text(full_text)

            # Insert chunks in bulk
            self._save_chunks(session, chunks, split_file.id)

            # Update status to success
            self._update_split_file_status(session, split_file, "chunk-success")
            self.logger.info(f"Successfully processed split file ID {split_file.id}.")
        except FileNotFoundError as e:
            self.logger.error(f"File not found for split file ID {split_file.id}: {e}")
            self._handle_processing_failure(session, split_file, "file-not-found")
        except Exception as e:
            self.logger.error(f"Error processing split file ID {split_file.id}: {e}")
            self._handle_processing_failure(session, split_file, "chunk-failed")

    @staticmethod
    def extract_markdown_with_metadata(file_path: Path, source_name: str) -> str:
        """
        Extracts the full Markdown content from a given PDF file while appending metadata such as
        source file name and page numbers.

        Args:
            file_path (Path): The path to the PDF file which needs to be converted.
            source_name (str): The name of the source file.

        Returns:
            str: A concatenated Markdown string with metadata.

        Raises:
            RuntimeError: If the file conversion fails.
        """
        try:
            pages: list[dict] = pymupdf4llm.to_markdown(
                str(file_path), page_chunks=True
            )

            def format_page(page: dict) -> str:
                """Formats a single page with its text and metadata."""
                metadata = page.get("metadata", {})
                page_number = (
                    f"\nPage Number: {metadata['page']}" if "page" in metadata else ""
                )
                return f"{page['text']}\n\nSource File: {source_name}{page_number}\n\n"

            return "".join(map(format_page, pages))

        except Exception as e:
            raise RuntimeError(f"Failed to convert file to Markdown: {e}")

    def _save_chunks(self, session: Session, chunks: list[str], split_file_id: int):
        """
        Saves chunks to the database in bulk.
        """
        if not chunks:
            self.logger.warning(
                f"No chunks generated for split file ID {split_file_id}."
            )
            return

        chunk_objects = [
            Chunk(content=chunk, split_file_id=split_file_id) for chunk in chunks
        ]
        session.bulk_save_objects(chunk_objects)
        session.commit()

    def _fetch_split_files_to_analyze(self, session: Session) -> list[SplitFile]:
        """
        Fetches split files that are pending analysis.
        """
        return (
            session.query(SplitFile)
            .filter(SplitFile.status == "wait-for-pymupdf4llm")
            .options(joinedload(SplitFile.file))  # Preload related File objects
            .all()
        )

    def _get_file_path_and_validate(self, split_file: SplitFile) -> Path:
        """
        Validates the file path for a given split file.
        """
        file_path = (
            self.path_config.get_split_dir_path(split_file.file.file_dir_name)
            / f"{split_file.split_id}.pdf"
        )
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist.")
        return file_path

    def _get_text_splitter(self) -> RecursiveCharacterTextSplitter:
        """
        Returns a configured text splitter instance.
        """
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
