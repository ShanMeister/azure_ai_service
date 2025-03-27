from sqlalchemy.orm import Session
import fitz

from ..repository.database import BaseSQLAgent
from ..repository.models import File, SplitFile
# from ..utils.logger_utils import LoggingAgent
from ..utils.config_utils import PathConfig, FileSplitterConfig
from ..utils.pdf_utils import SplitPDF, get_split_pdfs, extract_pages_to_pdf
from loguru import logger

class FileSplitter:
    """
    The FileSplitter module is designed for automated PDF file processing and management within a database-driven workflow. This module is a core component of a document processing pipeline, providing functionality for splitting large PDF files into smaller, manageable parts and updating their status in the database.
    """

    def __init__(self):
        """
        :param sql_agent: SQL agent for database operations.
        :param n_pages_per_split: Number of pages per split file.
        """
        # self.SessionLocal = sql_agent.SessionLocal
        self.file_splitter_config = FileSplitterConfig()
        self.n_pages_per_split = self.file_splitter_config.n_pages_per_split

        # self.logger = LoggingAgent("FileSplitter").logger
        self._path_config = PathConfig()

    def process_files(self, file):
        """
        Main interface to process files in batches using pdf_bytes.
        """
        # with self.SessionLocal() as session:
        #     while True:
        #         self._process_single_file(file, session)
        self._process_single_file(file)

    def _process_single_file(self, file):
        """
        Process a single PDF file in bytes: split into PDFs and update database.
        """
        try:
            split_files = []

            # 使用 fitz (PyMuPDF) 處理 pdf_bytes
            # split_pdfs = self._get_split_pdfs_from_bytes(pdf_bytes)
            split_pdfs = get_split_pdfs(
                self._path_config.get_done_dir(file.index_name, file.process_type),
                self._path_config.get_split_dir_path(file.file_dir_name),
                file,
                self.n_pages_per_split,
            )

            for split_pdf in split_pdfs:
                if self._extract_and_validate(split_pdf):
                    split_files.append(self._create_split_file_entry(split_pdf))
                else:
                    logger.error(f"Error extracting pages from PDF.")
                    # 更新檔案狀態為「處理失敗」
                    # self._update_file_status(session, file, "failed")

            # 如果有處理好的檔案，儲存進資料庫
            # if split_files:
            # self._save_split_files_to_db(session, split_files)

            logger.info(f"Successfully processed the file.")
        except Exception as e:
            logger.error(f"Error processing the file: {e}")

    # def _get_split_pdfs_from_bytes(self, pdf_bytes):
    #     """
    #     Get split PDFs from the provided pdf_bytes.
    #     """
    #     split_pdfs = []
    #
    #     # 使用 PyMuPDF (fitz) 打開 pdf_bytes 並進行分割處理
    #     pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    #     page_count = pdf_document.page_count
    #     split_size = self.n_pages_per_split  # 每個分割檔案的頁數
    #
    #     # 分割邏輯：根據頁數進行分割
    #     for i in range(0, page_count, split_size):
    #         split_pdf = pdf_document.extract_pages(i, min(i + split_size, page_count))
    #         split_pdfs.append(split_pdf)
    #
    #     pdf_document.close()  # 關閉 PDF 文檔
    #
    #     return split_pdfs

    # def process_files(self, pdf_bytes):
    #     """
    #     Main interface to process files in batches.
    #     """
    #     with self.SessionLocal() as session:
    #         while True:
    #             self._process_single_file(pdf_bytes, session)
    #
    # def _process_single_file(self, file: File, session: Session):
    #     """
    #     Process a single file: split into PDFs and update database.
    #     """
    #     try:
    #         split_files = []
    #         split_pdfs = get_split_pdfs(
    #             self._path_config.get_done_dir(file.index_name, file.process_type),
    #             self._path_config.get_split_dir_path(file.file_dir_name),
    #             file,
    #             self.n_pages_per_split,
    #         )
    #
    #         for split_pdf in split_pdfs:
    #             if self._extract_and_validate(split_pdf):
    #                 split_files.append(
    #                     self._create_split_file_entry(split_pdf, file.id)
    #                 )
    #             else:
    #                 self.logger.error(f"Error extracting pages for file {file.name}")
    #                 # self._update_file_status(session, file, "failed")
    #
    #         # if split_files:
    #         #     self._save_split_files_to_db(session, split_files)
    #
    #         # Update file status to 'processing'
    #         # self._update_file_status(session, file, "processing")
    #         self.logger.info(f"Successfully processed file {file.name}.")
    #     except Exception as e:
    #         self.logger.error(f"Error processing file {file.name}: {e}")
    #         session.rollback()
    #
    def _extract_and_validate(self, split_pdf: SplitPDF) -> bool:
        """
        Extract pages and validate success.
        """
        return extract_pages_to_pdf(logger, split_pdf)
    #
    def _create_split_file_entry(self, split_pdf: SplitPDF, file_id: int) -> SplitFile:
        """
        Create a SplitFile instance.
        """
        return SplitFile(
            split_id=split_pdf.split_id,
            start_page_number=split_pdf.start_page_id,
            n_pages=split_pdf.n_pages_in_target,
            status=split_pdf.status,
            file_id=file_id,
        )

    # def _save_split_files_to_db(self, session: Session, split_files: list[SplitFile]):
    #     """
    #     Save a batch of SplitFiles to the database.
    #     """
    #     session.bulk_save_objects(split_files)
    #     session.commit()
    #     self.logger.info(f"Saved {len(split_files)} split files to the database.")
    #
    # def _update_file_status(self, session: Session, file: File, status: str):
    #     """
    #     Update the status of a file.
    #     """
    #     file.status = status
    #     session.commit()
