from pathlib import Path
from logging import Logger
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .db_utils.database import BaseSQLAgent
from .db_utils.models import File
from .logger_utils import LoggingAgent
from .config_utils import PathConfig
from .pdf_utils import get_n_pages_from_pdf
from .comtypes_converter import WORD2PDFAgent, PPT2PDFAgent, EXCEL2PDFAgent


class MovingFileError(Exception):
    pass


class DirInitializer:

    def __init__(self, logger: Logger, file_folder_name: str, path_config: PathConfig):
        self.logger = logger
        self.file_folder_name = file_folder_name
        self.path_config = path_config

    def create_folders(self) -> None:
        self._create_dirs(
            [
                self.path_config.get_split_dir_path(self.file_folder_name),
                self.path_config.get_pkl_dir_path(self.file_folder_name),
                self.path_config.get_table_dir_path(self.file_folder_name),
                self.path_config.get_figure_dir_path(self.file_folder_name),
                self.path_config.get_raw_md_dir_path(self.file_folder_name),
                self.path_config.get_bundle_md_dir_path(self.file_folder_name),
            ]
        )

    def _create_dirs(self, dirs: list[Path]) -> None:
        for dir in dirs:
            if not dir.exists():
                dir.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created directory: {dir}")
            else:
                self.logger.warning(f"Directory already exists: {dir}")


class PDFScanner:
    """
    Scans directories and processes PDF files based on their `process_type`.
    """

    def __init__(self, sql_agent: BaseSQLAgent):
        """
        Initialize the PDFScanner with required configurations.

        :param sql_agent: SQL agent for database operations.
        """
        self.SessionLocal = sql_agent.SessionLocal
        self.logger = LoggingAgent("FileScanner").logger
        self._path_config = PathConfig()
        self.index_list = self._path_config.index_list

    def scan(self) -> None:
        """
        Scan and process files in the configured directories.
        """
        n_index = len(self.index_list)
        self.logger.info(f'Starting file scanning for {n_index} indices.')
        for index in self.index_list:
            self._process_directory(index, "text_image")

    def _process_directory(self, index: str, process_type: str) -> None:
        """
        Process all files in the given directory.

        :param process_type: Type of processing ('text' or 'text_image').
        """
        self.logger.debug(
            f"Scanning directory for (index={index}, process_type={process_type})"
        )
        wait_dir = self._path_config.get_wait_dir(index, process_type)
        done_dir = self._path_config.get_done_dir(index, process_type)
        fail_dir = self._path_config.get_fail_dir(index, process_type)
        pdf_files = list(wait_dir.rglob("*.pdf"))
        if not pdf_files:
            self.logger.debug(f"No files found in {wait_dir}")
            return
        self.logger.info(f"Found {len(pdf_files)} files in {wait_dir}")
        self._process_files(pdf_files, index, process_type, done_dir, fail_dir)

    def _process_files(
        self,
        pdf_files: list[Path],
        index: str,
        process_type: str,
        done_dir: Path,
        fail_dir: Path,
    ) -> None:
        """
        Process individual files and update the database.

        :param pdf_files: List of PDF file paths.
        :param index: Index identifier for the files.
        :param process_type: The process type of the files.
        :param done_dir: Directory to move successfully processed files to.
        :param fail_dir: Directory to move failed files to.
        """
        processed_files = []

        with self.SessionLocal() as session:
            for pdf_file in pdf_files:
                try:
                    # 為了讓user可以上傳重複的檔案，先暫時註解掉檢查流程
                    # if self._file_exists_in_db(session, pdf_file, index):
                    #     self.logger.warning(
                    #         f"File {pdf_file.name} already exists in the database with a non-deleted status."
                    #     )
                    #     self._move_file(pdf_file, fail_dir)  # Move failed files
                    #     continue

                    file_dir_name = uuid4().hex
                    file_record = self._create_file_record(
                        pdf_file, index, process_type, file_dir_name
                    )
                    DirInitializer(
                        self.logger, file_dir_name, self._path_config
                    ).create_folders()

                    session.add(file_record)
                    session.commit()  # Commit individually to avoid full rollback

                    # Move the file to done_dir after successful commit
                    self._move_file(pdf_file, done_dir)
                    processed_files.append(pdf_file)

                except SQLAlchemyError as e:
                    self.logger.error(
                        f"Database error occurred while processing {pdf_file.name}: {e}"
                    )
                    session.rollback()
                    self._move_file(pdf_file, fail_dir)  # Move failed files
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error occurred while processing {pdf_file.name}: {e}"
                    )
                    self._move_file(pdf_file, fail_dir)  # Move failed files

        self.logger.info(f"Finished processing {len(processed_files)} files successfully.")

    def _file_exists_in_db(
        self, session: Session, pdf_file: Path, index_name: str
    ) -> bool:
        """
        Check if a file of an index already exists in the database with a non-deleted status.

        :param session: Database session.
        :param pdf_file: Path to the file.
        :param index_name: Index name of the file. (Azure AI Search index name)
        :return: True if file exists, False otherwise.
        """
        return (
            session.query(File)
            .filter(
                File.index_name == index_name,
                File.name == pdf_file.name,
                File.status != "deleted",
            )
            .first()
            is not None
        )

    def _create_file_record(
        self, pdf_file: Path, index: str, process_type: str, file_dir_name: str
    ) -> File:
        """
        Create a database record for the given file.

        :param pdf_file: Path to the PDF file.
        :param process_type: The process type of the file.
        :param file_dir_name: Unique directory name for the file.
        :return: A `File` object.
        """
        try:
            n_pages = get_n_pages_from_pdf(pdf_file)
            size = pdf_file.stat().st_size
            return File(
                name=pdf_file.name,
                index_name=index,
                n_pages=n_pages,
                size=size,
                process_type=process_type,
                file_dir_name=file_dir_name,
            )
        except Exception as e:
            self.logger.error(f"Error processing file {pdf_file.name}: {e}")
            raise

    def _move_file(self, pdf_file: Path, destination_dir: Path) -> None:
        """
        Move the file to the destination directory.

        :param pdf_file: File to move.
        :param destination_dir: Directory to move the file to.
        """
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            pdf_file.replace(destination_dir / pdf_file.name)
            self.logger.info(f"Moved file {pdf_file.name} to {destination_dir}")
        except Exception as e:
            self.logger.error(f"Error moving file {pdf_file.name}: {e}")


class BaseOfficeScanner:
    def __init__(self, file_extension: str, agent_class):
        self.logger = LoggingAgent("FileScanner").logger
        self._path_config = PathConfig()
        self.index_list = self._path_config.index_list
        self.file_extension = file_extension
        self.agent_class = agent_class  # Class responsible for conversion

    def scan_and_convert(self):
        """
        Scan and process files in the configured directories sequentially.
        """
        for index in self.index_list:
            self._process_directory(index, "text_image")

    def _process_directory(self, index: str, process_type: str) -> None:
        """
        Process all files in the given directory.
        """
        wait_dir = self._path_config.get_wait_dir(index, process_type)
        done_dir = self._path_config.get_done_dir(index, process_type)
        fail_dir = self._path_config.get_fail_dir(index, process_type)

        files = list(
            wait_dir.rglob(f"*.{self.file_extension}*")
        )  # Handles ppt, pptx, doc, docx
        if not files:
            self.logger.debug(
                f"No {self.file_extension.upper()} files found in {wait_dir}"
            )
            return
        self.logger.info(
            f"Found {len(files)} {self.file_extension.upper()} files in {wait_dir}"
        )

        failed_files = []

        with self.agent_class() as agent:
            for input_path in files:
                output_path = wait_dir / f"{input_path.stem}.pdf"
                if output_path.exists():
                    self.logger.warning(f"Skipping {input_path}, PDF already exists.")
                    continue

                try:
                    agent.convert_to_pdf(input_path, output_path)
                    self._move_file(input_path, done_dir)
                    self.logger.info(f"Converted: {input_path} -> {output_path}")
                except Exception as e:
                    self.logger.error(f"Error converting {input_path}: {e}")
                    failed_files.append(input_path)

        if failed_files:
            for failed_file in failed_files:
                self._move_file(failed_file, fail_dir)
            self.logger.warning(
                f"Failed to convert {len(failed_files)} files in {wait_dir}"
            )

    def _move_file(self, file: Path, destination_dir: Path) -> None:
        """
        Move the file to the destination directory.
        """
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            file.replace(destination_dir / file.name)
            self.logger.info(f"Moved file {file.name} to {destination_dir}")
        except Exception as e:
            self.logger.error(f"Error moving file {file.name}: {e}")


class WORDScanner(BaseOfficeScanner):
    def __init__(self):
        super().__init__(file_extension="doc", agent_class=WORD2PDFAgent)


class PPTScanner(BaseOfficeScanner):
    def __init__(self):
        super().__init__(file_extension="ppt", agent_class=PPT2PDFAgent)


class EXCELScanner(BaseOfficeScanner):
    def __init__(self):
        super().__init__(file_extension="xls", agent_class=EXCEL2PDFAgent)
