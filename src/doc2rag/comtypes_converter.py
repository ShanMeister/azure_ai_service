from abc import ABC, abstractmethod
import comtypes.client
from pathlib import Path
import threading
import pythoncom


class ConvertPDFError(Exception):
    """Custom exception for conversion errors."""

    pass


class BaseOffice2PDFAgent(ABC):
    MAX_CONVERT_TIME = 600  # Maximum conversion time in seconds: 10 minutes

    def __init__(self):
        """Initialize the respective Office application."""
        pythoncom.CoInitialize()  # Initialize COM in the main thread
        self.app = self.create_application()

    @abstractmethod
    def create_application(self):
        """Create the specific Office application instance."""
        pass

    @abstractmethod
    def open_document(self, input_path: Path):
        """Open the document in the respective application."""
        pass

    @abstractmethod
    def save_as_pdf(self, document, output_path: Path):
        """Save the document as a PDF."""
        pass

    def convert_to_pdf(self, input_path: Path, output_path: Path):
        """Template method for converting Office documents to PDFs with a timeout."""
        timeout_flag = False

        def timeout_handler():
            nonlocal timeout_flag
            timeout_flag = True
            self.close()  # Force close Office application

        timer = threading.Timer(self.MAX_CONVERT_TIME, timeout_handler)
        timer.start()

        try:
            document = self.open_document(input_path)
            self.save_as_pdf(document, output_path)
            document.Close()
            timer.cancel()
        except Exception as e:
            timer.cancel()
            raise ConvertPDFError(f"Error converting {input_path}: {e}")

        if timeout_flag:
            raise ConvertPDFError(f"Conversion timeout exceeded for {input_path}")

    def close(self):
        """Close the Office application."""
        self.app.Quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class WORD2PDFAgent(BaseOffice2PDFAgent):
    def create_application(self):
        word_app = comtypes.client.CreateObject("Word.Application")
        word_app.Visible = False
        return word_app

    def open_document(self, input_path: Path):
        return self.app.Documents.Open(str(input_path))

    def save_as_pdf(self, document, output_path: Path):
        document.SaveAs(str(output_path), FileFormat=17)  # 17 = PDF format


class PPT2PDFAgent(BaseOffice2PDFAgent):
    def create_application(self):
        ppt_app = comtypes.client.CreateObject("PowerPoint.Application")
        ppt_app.Visible = True  # Must be visible for PowerPoint
        return ppt_app

    def open_document(self, input_path: Path):
        return self.app.Presentations.Open(str(input_path))

    def save_as_pdf(self, document, output_path: Path):
        document.SaveAs(str(output_path), FileFormat=32)  # 32 = PDF format


class EXCEL2PDFAgent(BaseOffice2PDFAgent):
    def create_application(self):
        excel_app = comtypes.client.CreateObject("Excel.Application")
        excel_app.Visible = False  # Run in the background
        return excel_app

    def open_document(self, input_path: Path):
        return self.app.Workbooks.Open(str(input_path))

    def save_as_pdf(self, document, output_path: Path):
        document.ExportAsFixedFormat(0, str(output_path))  # 0 = PDF format

    def close(self):
        """Override close method to ensure Excel quits properly."""
        if self.app:
            self.app.Quit()


def word2pdf_example():
    word2pdf = WORD2PDFAgent()
    input_path = Path("example.docx")
    output_path = Path("example.pdf")
    word2pdf.convert_to_pdf(input_path, output_path)


def ppt2pdf_example():
    ppt2pdf = PPT2PDFAgent()
    input_path = Path("example.pptx")
    output_path = Path("example.pdf")
    ppt2pdf.convert_to_pdf(input_path, output_path)


def excel2pdf_example():
    excel2pdf = EXCEL2PDFAgent()
    input_path = Path("example.xlsx")
    output_path = Path("example.pdf")
    excel2pdf.convert_to_pdf(input_path, output_path)
    