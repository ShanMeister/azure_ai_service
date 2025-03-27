import fitz
from logging import Logger
from pathlib import Path
# from PyPDF2 import PdfReader
from pydantic import BaseModel, PositiveInt

from ..repository.models import File


class SplitPDF(BaseModel):
    """
    Pydantic model to validate inputs for the extract_pages_to_pdf function.
    """
    pdf_bytes: bytes  # PDF content as bytes
    start_page_id: PositiveInt  # 1-based positive integer
    end_page_id: PositiveInt  # 1-based positive integer
    target_path: str  # new_pdf_file_path
    n_pages_in_source: PositiveInt  # Total number of pages in the source PDF
    n_pages_in_target: PositiveInt  # Total number of pages in the target PDF
    split_id: int  # Identifier for the split
    status: str  # wait-for-pymupdf4llm, wait-for-di

    # source_path: Path  # original_pdf_path
    # start_page_id: PositiveInt  # 1-based positive integer
    # end_page_id: PositiveInt  # 1-based positive integer
    # target_path: Path  # new_pdf_file_path
    # n_pages_in_source: PositiveInt  # Total number of pages in the source PDF
    # n_pages_in_target: PositiveInt  # Total number of pages in the target PDF
    # split_id: int  # Identifier for the split
    # status: str  # wait-for-pymupdf4llm, wait-for-di

    def validate_page_range(self):
        """
        Additional validation to check if the page range is valid with respect to n_pages_in_source.

        Raises:
            ValueError: If start_page_id or end_page_id is invalid.
        """
        if self.start_page_id > self.end_page_id:
            raise ValueError("start_page_id must be less than or equal to end_page_id.")
        if self.end_page_id > self.n_pages_in_source:
            raise ValueError(
                f"Page range out of bounds. The source PDF has {self.n_pages_in_source} pages."
            )
        # Validate n_pages_in_target based on the selected range
        expected_target_pages = self.end_page_id - self.start_page_id + 1
        if self.n_pages_in_target != expected_target_pages:
            raise ValueError(
                f"n_pages_in_target should match the page range. "
                f"Expected {expected_target_pages}, got {self.n_pages_in_target}."
            )

    def validate_source_exists(self):
        """Check if the source PDF file exists."""
        if not self.source_path.exists():
            raise FileNotFoundError(
                f"The source file '{self.source_path}' does not exist."
            )


def get_n_pages_from_pdf(pdf_file: Path) -> int:
    """Get the number of pages in a PDF file."""
    with pdf_file.open("rb") as f:
        reader = PdfReader(f)
        n_pages = len(reader.pages)
    return n_pages


def get_filename_prefix(filename: str) -> str:
    """
    Extracts the prefix of a filename by removing the final file extension.
    Handles multiple dots and spaces in filenames.

    Parameters:
        filename (str): The filename to process.

    Returns:
        str: The prefix of the filename without the final extension.

    Example usage:
        print(get_filename_prefix("xxx.pdf"))  # -> "xxx"
        print(get_filename_prefix("xxx.1.pdf"))  # -> "xxx.1"
        print(get_filename_prefix("xxx.1.202405.pdf"))  # -> "xxx.1.202405"
        print(get_filename_prefix("xxx yyy .1.pdf"))  # -> "xxx yyy.1"
    """
    # Convert the filename to a Path object
    path = Path(filename.strip())  # Strip leading/trailing spaces for safety

    # Get the stem (removes the final extension)
    return path.stem


def get_split_pdfs(
    done_dir: Path, split_dir: Path, file: File, n_pages_per_split: int
) -> list[SplitPDF]:
    """
    Generate a list of SplitPDF objects based on the File object.

    Args:
        done_dir (Path): Path to the directory containing processed files.
        split_dir (Path): Path to the directory where split PDFs will be saved.
        file (File): File object from the database, containing metadata.
        n_pages_per_split (int): Number of pages per split.

    Returns:
        List[SplitPDF]: List of SplitPDF objects with split PDF details.
    """
    if n_pages_per_split <= 0:
        raise ValueError("n_pages_per_split must be a positive integer.")

    pdf_file = done_dir / file.name
    n_pages = file.n_pages

    if n_pages == 0:
        return []  # No pages to split

    n_splits, remainder = divmod(n_pages, n_pages_per_split)
    if remainder > 0:
        n_splits += 1  # Account for remaining pages in the last split

    split_pdfs = []

    for split_id in range(n_splits):
        start_page = split_id * n_pages_per_split + 1
        end_page = min((split_id + 1) * n_pages_per_split, n_pages)
        n_pages_in_target = end_page - start_page + 1
        target_file_name = f"{split_id}.pdf"
        target_file_path = split_dir / target_file_name

        # Assign status based on process type
        status = (
            "wait-for-pymupdf4llm" if file.process_type == "text" else "wait-for-di"
        )

        split_pdf = SplitPDF(
            source_path=pdf_file,
            start_page_id=start_page,
            end_page_id=end_page,
            target_path=target_file_path,
            n_pages_in_source=n_pages,
            n_pages_in_target=n_pages_in_target,
            split_id=split_id,
            status=status,
        )
        split_pdfs.append(split_pdf)

    return split_pdfs


def extract_pages_to_pdf(logger: Logger, pdf_input: SplitPDF) -> bool:
    """
    Extract a range of pages from a PDF file and save them to a new PDF file using validated inputs.

    Args:
        logger (Logger): Logger instance for logging messages.
        pdf_input (SplitPDF): Validated Pydantic model containing all required inputs.

    Returns:
        bool: True if the extraction is successful, False otherwise.
    """
    try:
        # Perform validation on the page range
        pdf_input.validate_page_range()

        # Perform validation on the source file
        pdf_input.validate_source_exists()

        # Open the source PDF file
        with fitz.open(pdf_input.source_path) as doc:
            # Ensure the source PDF has the expected number of pages
            if len(doc) != pdf_input.n_pages_in_source:
                logger.error(
                    f"Mismatch in the source PDF page count. "
                    f"Expected {pdf_input.n_pages_in_source}, found {len(doc)}."
                )
                return False

            # Create a new PDF document for the output
            new_doc = fitz.open()
            new_doc.insert_pdf(
                doc,
                from_page=pdf_input.start_page_id - 1,
                to_page=pdf_input.end_page_id - 1,
                annots=True,
            )

            # Validate the number of pages in the target PDF
            n_pages = len(new_doc)
            if n_pages != pdf_input.n_pages_in_target:
                logger.error(
                    f"Mismatch in the target PDF page count. "
                    f"Expected {pdf_input.n_pages_in_target}, got {n_pages}."
                )
                return False

            # Write to the target file
            new_doc.save(pdf_input.target_path)

        logger.debug(f"New PDF created: {pdf_input.target_path}")
        return True

    except Exception as e:
        logger.error(f"Error occurred while extracting pages: {e}")
        return False


# import fitz
# from logging import Logger
# from pydantic import BaseModel, PositiveInt
# from io import BytesIO
#
#
# class SplitPDF(BaseModel):
#     """
#     Pydantic model to validate inputs for the extract_pages_to_pdf function.
#     """
#
#     pdf_bytes: bytes  # PDF content as bytes
#     start_page_id: PositiveInt  # 1-based positive integer
#     end_page_id: PositiveInt  # 1-based positive integer
#     target_path: str  # new_pdf_file_path
#     n_pages_in_source: PositiveInt  # Total number of pages in the source PDF
#     n_pages_in_target: PositiveInt  # Total number of pages in the target PDF
#     split_id: int  # Identifier for the split
#     status: str  # wait-for-pymupdf4llm, wait-for-di
#
#     def validate_page_range(self):
#         """
#         Additional validation to check if the page range is valid with respect to n_pages_in_source.
#
#         Raises:
#             ValueError: If start_page_id or end_page_id is invalid.
#         """
#         if self.start_page_id > self.end_page_id:
#             raise ValueError("start_page_id must be less than or equal to end_page_id.")
#         if self.end_page_id > self.n_pages_in_source:
#             raise ValueError(
#                 f"Page range out of bounds. The source PDF has {self.n_pages_in_source} pages."
#             )
#         # Validate n_pages_in_target based on the selected range
#         expected_target_pages = self.end_page_id - self.start_page_id + 1
#         if self.n_pages_in_target != expected_target_pages:
#             raise ValueError(
#                 f"n_pages_in_target should match the page range. "
#                 f"Expected {expected_target_pages}, got {self.n_pages_in_target}."
#             )
#
#
# def get_n_pages_from_pdf(pdf_bytes: bytes) -> int:
#     """Get the number of pages in a PDF file from bytes."""
#     with BytesIO(pdf_bytes) as pdf_stream:
#         doc = fitz.open(pdf_stream)
#         return len(doc)
#
#
# def extract_pages_to_pdf(logger: Logger, pdf_input: SplitPDF) -> bool:
#     """
#     Extract a range of pages from a PDF file and save them to a new PDF file using validated inputs.
#
#     Args:
#         logger (Logger): Logger instance for logging messages.
#         pdf_input (SplitPDF): Validated Pydantic model containing all required inputs.
#
#     Returns:
#         bool: True if the extraction is successful, False otherwise.
#     """
#     try:
#         # Perform validation on the page range
#         pdf_input.validate_page_range()
#
#         # Create a file-like object from the pdf_bytes
#         pdf_stream = BytesIO(pdf_input.pdf_bytes)
#
#         # Open the source PDF file
#         with fitz.open(pdf_stream) as doc:
#             # Ensure the source PDF has the expected number of pages
#             if len(doc) != pdf_input.n_pages_in_source:
#                 logger.error(
#                     f"Mismatch in the source PDF page count. "
#                     f"Expected {pdf_input.n_pages_in_source}, found {len(doc)}."
#                 )
#                 return False
#
#             # Create a new PDF document for the output
#             new_doc = fitz.open()
#             new_doc.insert_pdf(
#                 doc,
#                 from_page=pdf_input.start_page_id - 1,
#                 to_page=pdf_input.end_page_id - 1,
#                 annots=True,
#             )
#
#             # Validate the number of pages in the target PDF
#             n_pages = len(new_doc)
#             if n_pages != pdf_input.n_pages_in_target:
#                 logger.error(
#                     f"Mismatch in the target PDF page count. "
#                     f"Expected {pdf_input.n_pages_in_target}, got {n_pages}."
#                 )
#                 return False
#
#             # Write to the target file
#             new_doc.save(pdf_input.target_path)
#
#         logger.debug(f"New PDF created: {pdf_input.target_path}")
#         return True
#
#     except Exception as e:
#         logger.error(f"Error occurred while extracting pages: {e}")
#         return False