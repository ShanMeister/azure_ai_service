import pymupdf4llm
from io import BytesIO
import fitz  # PyMuPDF
# from pymupdf4llm.helpers.pymupdf_rag import extract_markdown_from_doc
import pymupdf.pro
from fastapi import UploadFile
pymupdf.pro.unlock()


class FileProcessUseCase:
    def __init__(self):
        pass

    async def get_markdown_with_pymupdf4llm(self, file: UploadFile):
        try:
            file_bytes = await file.read()
            file_stream = BytesIO(file_bytes)

            doc = fitz.open(stream=file_stream, filetype="pdf")

            document = pymupdf4llm.to_markdown(doc)
            return document
        except Exception as e:
            raise RuntimeError(f"Failed to parse file via pymupdf4llm: {e}")
