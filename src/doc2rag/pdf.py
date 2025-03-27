from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import PyPDF2

from .db_utils.models import File, Page
from ..db_utils.sqlite.database import SQliteAgent
from .config_utils import PathConfig
from .logger_utils import LoggingAgent


TAIPEI_ZONEINFO = ZoneInfo("Asia/Taipei")


class PDFAgent:
    def __init__(self):
        self.logger = LoggingAgent("PDFAgent").logger
        self.path_config = PathConfig()
        self.SessionLocal = SQliteAgent().SessionLocal

        self.unprocessed_dir = self.path_config.unprocessed_dir_path
        self.processed_dir = self.path_config.processed_dir_path

    def main(self):
        """Main function to scan and process new PDFs."""
        pdf_files = self.scan_for_new_pdfs()
        if pdf_files:
            self.logger.info(f"Processing {len(pdf_files)} PDF(s): {pdf_files}")
            for pdf_file in pdf_files:
                self.process_pdf(pdf_file)
        else:
            self.logger.info("No new PDFs found.")

    def scan_for_new_pdfs(self):
        """Scan the unprocessed directory for new PDFs."""
        pdf_files = [f for f in self.unprocessed_dir.iterdir() if f.suffix == ".pdf"]
        self.logger.info(f"Found {len(pdf_files)} PDF(s) in {self.unprocessed_dir}.")
        return pdf_files

    def process_pdf(self, pdf_file: Path):
        """Process a single PDF, split it into pages, and store it in the database."""
        with self.SessionLocal() as session:
            try:
                # Check if this file has already been processed
                if session.query(File).filter_by(file_name=pdf_file.name).first():
                    self.logger.info(
                        f"File {pdf_file.name} has already been processed."
                    )
                    return

                with pdf_file.open("rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    n_pages = len(reader.pages)
                    size = pdf_file.stat().st_size / (1024 * 1024)  # Size in MB

                    # Create a new File record
                    new_file = File(
                        file_name=pdf_file.name,
                        n_pages=n_pages,
                        size=size,
                        upload_time=datetime.now(TAIPEI_ZONEINFO),
                    )
                    session.add(new_file)
                    session.flush()  # Flush to get the new_file.id before bulk saving pages

                    self.logger.info(
                        f"Processing PDF: {pdf_file.name}, Pages: {n_pages}, Size: {size:.2f} MB"
                    )

                    # Prepare directory for metadata
                    metadata_dir = self.path_config.metadata_dir_path / pdf_file.stem
                    metadata_dir.mkdir(parents=True, exist_ok=True)

                    # Process pages in bulk and avoid multiple commits
                    new_pages = []
                    for page_num in range(n_pages):
                        metadata_page_dir = metadata_dir / f"page_{page_num + 1}"
                        metadata_page_dir.mkdir(parents=True, exist_ok=True)

                        # Extract the specified page
                        with PyPDF2.PdfWriter() as pdf_writer:
                            pdf_writer.add_page(reader.pages[page_num])
                            output_single_page_pdf_path = metadata_page_dir / "raw.pdf"
                            with open(
                                output_single_page_pdf_path, "wb"
                            ) as output_pdf_file:
                                pdf_writer.write(output_pdf_file)

                        # Add page to the list for bulk insertion
                        new_pages.append(
                            Page(
                                file_id=new_file.id,
                                page_number=page_num + 1,
                                is_active=True,
                            )
                        )

                        # Log progress every 10 pages
                        if (page_num + 1) % 10 == 0 or page_num == n_pages - 1:
                            self.logger.info(f"Processed: {page_num + 1} / {n_pages}.")

                    # Bulk insert all pages and commit once
                    session.bulk_save_objects(new_pages)
                    session.commit()

                self.logger.info(f"File {pdf_file.name} processed successfully.")

                # Move the file to the processed directory
                self.move_to_processed(pdf_file)

            except Exception as e:
                self.logger.error(
                    f"Error processing file {pdf_file.name}: {e}", exc_info=True
                )

    def move_to_processed(self, pdf_file: Path):
        """Move a processed PDF to the processed directory."""
        try:
            dest_path = self.processed_dir / pdf_file.name
            pdf_file.rename(dest_path)
            self.logger.info(f"Moved {pdf_file.name} to {self.processed_dir}.")
        except Exception as e:
            self.logger.error(
                f"Error moving file {pdf_file.name} to {self.processed_dir}: {e}",
                exc_info=True,
            )
