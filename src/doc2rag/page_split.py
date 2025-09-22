from typing import List, Union
from pathlib import Path
from logging import Logger
import pickle

from azure.ai.documentintelligence.models import AnalyzeResult
from sqlalchemy.orm import Session, joinedload
from bs4 import BeautifulSoup
from markdownify import markdownify
import fitz
from PIL import Image

from .db_utils.database import BaseSQLAgent
from .logger_utils import LoggingAgent
from .config_utils import PathConfig
from .db_utils.models import SplitFile, Page, Table, Figure


class PklNotExistsError(Exception):
    pass


class PageNumberNotMatchError(Exception):
    pass


def get_page_number(split_file: SplitFile, page_id_in_split_file: int) -> int:
    """
    Calculate the real page number from the split file's starting page.

    Args:
        split_file (SplitFile): Metadata about the split file.
        page_id_in_split_file (int): Page ID in the split file. (starts from 1)
    """
    return split_file.start_page_number + page_id_in_split_file - 1


def save_to_file(content: str, path: Path, logger: Logger, description: str = "file"):
    """
    Save content to a file at the given path, with error handling.

    Args:
        content (str): Content to save.
        path (Path): Path where the content should be saved.
        logger (Logger): Logger instance for logging.
        description (str): Description of the file type for logging purposes.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Saved {description} to {path}.")
    except IOError as e:
        logger.error(f"Failed to save {description} to {path}: {e}")
        raise


def save_to_db(
    session: Session,
    objects: List[Union[Page, Table, Figure]],
    logger: Logger,
    object_name: str = "object",
):
    """
    Save a list of objects to the database.

    Args:
        session (Session): Database session.
        objects (List[Base]): List of SQLAlchemy objects to save.
        logger (Logger): Logger instance for logging messages.
        object_name (str): Name of the object type for logging purposes.
    """
    if not objects:
        logger.info(f"No {object_name}s to save to the database.")
        return

    try:
        session.add_all(objects)
        session.commit()
        logger.info(f"Saved {len(objects)} {object_name}(s) to the database.")
    except Exception as e:
        logger.error(f"Failed to save {object_name}s to the database: {e}")
        session.rollback()
        raise


def get_file_path(base_dir: Path, *components: int, extension: str) -> Path:
    """
    Generalized method to construct file paths dynamically.

    Args:
        base_dir (Path): The base directory for the file.
        *components (int): Components of the file name.
        extension (str): File extension including the dot (e.g., '.md', '.png').

    Returns:
        Path: Constructed file path.
    """
    file_name = "_".join(map(str, components)) + extension
    return base_dir / file_name


class SplitFilesProcessor:
    """
    Main controller for processing pages.
    """

    def __init__(self, sql_agent: BaseSQLAgent):
        self.logger = LoggingAgent("PageSplitter").logger
        self.SessionLocal = sql_agent.SessionLocal

    async def run(self):
        """
        Main entry point to process split files and perform page splitting.
        """
        with self.SessionLocal() as session:
            split_files = self._fetch_split_files_to_do_page_split(session)
            if not split_files:
                self.logger.info("No files to analyze.")
                return

            self.logger.info(f"Found {len(split_files)} files to analyze.")
            for split_file in split_files:
                self._process_single_file(session, split_file)

    def _process_single_file(self, session: Session, split_file: SplitFile):
        """
        Process a single split file.
        """
        try:
            self.logger.info(f"Start Processing (splitfile-id = {split_file.id})")
            pages_splitter = PagesSplitter(self.logger, session, split_file)
            page_id_in_sql_table_lst = pages_splitter.process_pages()
            pages_splitter.process_tables(page_id_in_sql_table_lst)
            pages_splitter.process_figures(page_id_in_sql_table_lst)
            self._update_split_file_status(session, split_file, "page-split-success")
        except Exception as e:
            self.logger.error(
                f"Error processing file {split_file.id}: {e}", exc_info=True
            )
            self._update_split_file_status(session, split_file, "page-split-failed")

    def _fetch_split_files_to_do_page_split(self, session: Session) -> List[SplitFile]:
        """
        Fetch split files with status 'di-success' that need page splitting.
        """
        self.logger.debug("Fetching files with status 'di-success'.")
        return (
            session.query(SplitFile)
            .filter(SplitFile.status == "di-success")
            .options(joinedload(SplitFile.file))
            .all()
        )

    def _update_split_file_status(
        self, session: Session, split_file: SplitFile, status: str
    ):
        """
        Update the status of a split file and commit the session.
        """
        try:
            split_file.status = status
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(
                f"Failed to update status for (splitfile-id = {split_file.id}): {e}",
                exc_info=True,
            )


class PagesSplitter:
    def __init__(
        self,
        logger: Logger,
        session: Session,
        split_file: SplitFile,
    ) -> None:
        self.logger = logger
        self.session = session
        self.split_file = split_file
        self._path_config = PathConfig()

        self.result = self._load_analysis_result()
        self.page_content_list = self._extract_page_contents()

        self.is_tables_need_to_be_processed = bool(self.result.tables)
        self.is_figures_need_to_be_processed = bool(self.result.figures)

    def process_pages(self) -> list[int]:
        """
        Processes all pages using the PageProcessor and returns a list of processed page IDs.
        """
        page_processor = PageProcessor(
            self.session,
            self.logger,
            self.split_file,
            self._path_config,
            self.page_content_list,
        )
        page_processor.run()
        return page_processor.get_page_id_lst()

    def process_tables(self, page_id_in_sql_table_lst: list[int]):
        """
        Processes tables if required using the TableProcessor.
        """
        if not self.is_tables_need_to_be_processed:
            return
        TableProcessor(
            self.session,
            self.logger,
            self.split_file,
            self._path_config,
            self.page_content_list,
            page_id_in_sql_table_lst,
        ).run()

    def process_figures(self, page_id_in_sql_table_lst: list[int]):
        """
        Processes figures if required using the FigureProcessor.
        """
        if not self.is_figures_need_to_be_processed:
            return
        FigureProcessor(
            self.session,
            self.logger,
            self.split_file,
            self._path_config,
            self.result,
            page_id_in_sql_table_lst,
        ).run()

    def _load_analysis_result(self) -> AnalyzeResult:
        """
        Loads the analysis result from a pickle file.
        Raises an exception if the file is missing.
        """
        pkl_path = (
            self._path_config.get_pkl_dir_path(self.split_file.file.file_dir_name)
            / f"{self.split_file.split_id}.pkl"
        )

        if not pkl_path.exists():
            raise PklNotExistsError(f"Pickle file {pkl_path} does not exist.")

        with open(pkl_path, "rb") as f:
            return pickle.load(f)

    def _extract_page_contents(self) -> list[str]:
        """
        Splits the analysis result's content into pages based on the PageBreak marker.
        Ensures the number of extracted pages matches the expected number of pages.
        """
        page_contents = self.result.content.split("<!-- PageBreak -->")
        if len(page_contents) != self.split_file.n_pages:
            raise PageNumberNotMatchError(
                f"Page count mismatch: "
                f"Expected {self.split_file.n_pages}, found {len(page_contents)}."
            )
        return page_contents


class PageProcessor:
    """
    Processes and saves pages with raw markdown content, updates the database.
    """

    def __init__(
        self,
        session: Session,
        logger: Logger,
        split_file: SplitFile,
        path_config: PathConfig,
        page_content_list: List[str],
    ) -> None:
        """
        Initializes the PageProcessor with required dependencies and configurations.

        Args:
            session (Session): Database session.
            logger (Logger): Logger instance for logging messages.
            split_file (SplitFile): Metadata about the split file.
            path_config (PathConfig): Path configuration for raw markdown directory.
            page_content_list (List[str]): List of raw page content strings.
        """
        self.session = session
        self.logger = logger
        self.split_file = split_file
        self.path_config = path_config
        self.page_content_list = page_content_list

        # Precompute values that are reused
        self.file_id = split_file.file_id
        self.split_file_id = split_file.id
        self.raw_md_dir_path = self._get_raw_md_dir_path()

        # Store processed Page objects
        self.page_lst: List[Page] = []

    def run(self):
        """Main method to process and save pages."""
        for page_id_in_split_file, page_content in enumerate(
            self.page_content_list, start=1
        ):
            page_number = get_page_number(self.split_file, page_id_in_split_file)
            raw_md_path = self._get_raw_md_path(page_number)

            # Save markdown content and prepare Page object
            self._save_raw_md(page_content, raw_md_path)
            self.page_lst.append(
                Page(
                    page_number=page_number,
                    page_id_in_split_file=page_id_in_split_file,
                    status="raw-md-extracted",
                    split_file_id=self.split_file_id,
                )
            )

        # Persist processed pages to the database
        self._save_pages_to_db()

    def get_page_id_lst(self) -> List[int]:
        """Retrieve a list of IDs of the processed pages."""
        return [page.id for page in self.page_lst]

    def _get_raw_md_dir_path(self) -> Path:
        """Get the directory path for raw markdown files."""
        return self.path_config.get_raw_md_dir_path(self.split_file.file.file_dir_name)

    def _get_raw_md_path(self, page_number: int) -> Path:
        """Construct the raw markdown file path for a given page number."""
        return get_file_path(self.raw_md_dir_path, page_number, extension=".md")

    def _save_raw_md(self, content: str, path: Path):
        """Save raw markdown content to the specified path."""
        save_to_file(content, path, self.logger, "raw markdown")

    def _save_pages_to_db(self):
        """Persist all Page objects to the database."""
        save_to_db(self.session, self.page_lst, self.logger, "page")


class TableProcessor:
    """
    Processes tables extracted from HTML content in pages, saves them as markdown files,
    and updates the database with table metadata.
    """

    def __init__(
        self,
        session: Session,
        logger: Logger,
        split_file: SplitFile,
        path_config: PathConfig,
        page_content_list: List[str],
        page_id_in_sql_table_lst: List[int],
    ) -> None:
        """
        Initializes the TableProcessor.

        Args:
            session (Session): Database session.
            logger (Logger): Logger instance for logging messages.
            split_file (SplitFile): Metadata about the split file.
            path_config (PathConfig): Path configuration for table directories.
            page_content_list (List[str]): List of HTML content for each page.
            page_id_in_sql_table_lst (List[int]): List of page IDs corresponding to SQL "Page" table.

        Raises:
            PageNumberNotMatchError: If the number of pages does not match the number of IDs in the table list.
        """
        self.session = session
        self.logger = logger
        self.split_file = split_file
        self.path_config = path_config
        self.page_content_list = page_content_list
        self.page_id_in_sql_table_lst = page_id_in_sql_table_lst

        # Precompute table directory path
        self.table_dir_path = self._get_table_dir_path()

        # Validate the input
        if len(page_content_list) != len(page_id_in_sql_table_lst):
            raise PageNumberNotMatchError(
                "Number of pages does not match the number of pages in the table list."
            )

        # Store processed Table objects
        self.table_lst: List[Table] = []

    def run(self):
        """Main method to process and save tables from the page content."""
        for page_id_in_split_file, (page_id_in_sql_table, page_content) in enumerate(
            zip(self.page_id_in_sql_table_lst, self.page_content_list), start=1
        ):
            page_number = get_page_number(self.split_file, page_id_in_split_file)
            soup = BeautifulSoup(page_content, "html.parser")
            tables = soup.find_all("table")

            for table_id_in_page, table in enumerate(tables, start=1):
                # Convert table to markdown
                markdown_table = markdownify(str(table))
                table_path = self._get_table_path(page_number, table_id_in_page)

                # Save markdown table and append metadata
                self._save_table(markdown_table, table_path)
                self.table_lst.append(
                    Table(
                        page_number=page_number,
                        table_id_in_page=table_id_in_page,
                        page_id=page_id_in_sql_table,
                    )
                )

        # Save all table metadata to the database
        self._save_tables_to_db()

    def _get_table_dir_path(self) -> Path:
        """Get the directory path for table files."""
        return self.path_config.get_table_dir_path(self.split_file.file.file_dir_name)

    def _get_table_path(self, page_number: int, table_id_in_page: int) -> Path:
        """
        Construct the path for saving a table as a markdown file.
        """
        return get_file_path(
            self.table_dir_path, page_number, table_id_in_page, extension=".md"
        )

    def _save_table(self, table_content: str, table_path: Path):
        """
        Save a table's markdown content to the specified file path.

        Args:
            table_content (str): Table content in markdown format.
            table_path (Path): File path to save the table.
        """
        save_to_file(table_content, table_path, self.logger, "table")

    def _save_tables_to_db(self):
        """Persist all Table objects to the database."""
        save_to_db(self.session, self.table_lst, self.logger, "table")


class FigureProcessor:
    """
    Processes figures extracted from PDF pages, saves them as images,
    and updates the database with figure metadata.
    """

    def __init__(
        self,
        session: Session,
        logger: Logger,
        split_file: SplitFile,
        path_config: PathConfig,
        analyze_result: AnalyzeResult,
        page_id_in_sql_table_lst: List[int],
    ) -> None:
        self.session = session
        self.logger = logger
        self.split_file = split_file
        self.path_config = path_config
        self.analyze_result = analyze_result
        self.page_id_in_sql_table_lst = page_id_in_sql_table_lst

        # Precompute directory paths
        self.figure_dir_path = self.path_config.get_figure_dir_path(
            self.split_file.file.file_dir_name
        )
        self.split_dir_path = self.path_config.get_split_dir_path(
            self.split_file.file.file_dir_name
        )

        self.figure_lst: List[Figure] = []

    def run(self):
        """Main method to process and save figures from the page content."""
        pdf_path = self._get_split_pdf_path()

        with fitz.open(pdf_path) as doc:
            for figure_dict in self.analyze_result.figures:
                self._process_single_figure(figure_dict, doc)

        # Save all figure metadata to the database
        self._save_figures_to_db()

    def _process_single_figure(self, figure_dict: dict, doc: fitz.Document):
        """Processes a single figure."""
        page_id_in_split_file, figure_id_in_page = self._get_page_and_figure_id(
            figure_dict["id"]
        )
        page_number = get_page_number(self.split_file, page_id_in_split_file)
        bounding_box = self._get_bound_box(figure_dict)

        page = doc.load_page(page_id_in_split_file - 1)
        img = self._crop_image_from_pdf_page(page, bounding_box)

        figure_path = self._get_figure_path(page_number, figure_id_in_page)
        self._save_figure(img, figure_path)

        page_id = self.page_id_in_sql_table_lst[page_id_in_split_file - 1]
        self.figure_lst.append(
            Figure(
                page_number=page_number,
                figure_id_in_page=figure_id_in_page,
                page_id=page_id,
            )
        )

    def _get_page_and_figure_id(self, figure_id: str) -> tuple[int, int]:
        """Extract page-id in split file and figure-id in page from the figure ID."""
        return map(int, figure_id.split("."))

    def _get_bound_box(self, figure_data: dict) -> List[float]:
        """Extract bounding box coordinates from figure data."""
        polygon = figure_data["boundingRegions"][0]["polygon"]
        return [
            min(polygon[0::2]),
            min(polygon[1::2]),
            max(polygon[0::2]),
            max(polygon[1::2]),
        ]

    def _crop_image_from_pdf_page(
        self, page: fitz.Page, bounding_box: List[float]
    ) -> Image:
        rect = fitz.Rect([x * 72 for x in bounding_box])
        pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), clip=rect)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def _get_split_pdf_path(self) -> Path:
        return self.split_dir_path / f"{self.split_file.split_id}.pdf"

    def _get_figure_path(self, page_number: int, figure_id_in_page: int) -> Path:
        """Construct the path for saving a figure."""
        return get_file_path(
            self.figure_dir_path, page_number, figure_id_in_page, extension=".png"
        )

    def _save_figure(self, image: Image, figure_path: Path):
        try:
            figure_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(str(figure_path), format="PNG")
            self.logger.debug(f"Saved figure to {figure_path}.")
        except IOError as e:
            self.logger.error(f"Failed to save figure to {figure_path}: {e}")
            raise

    def _save_figures_to_db(self):
        """Persist all Figure objects to the database."""
        save_to_db(self.session, self.figure_lst, self.logger, "figure")
