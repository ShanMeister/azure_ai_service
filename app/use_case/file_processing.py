import io
import os
import pymupdf4llm
import subprocess
from io import BytesIO
import tempfile
import fitz  # PyMuPDF
# from pymupdf4llm.helpers.pymupdf_rag import extract_markdown_from_doc
# import pymupdf.pro
from fastapi import UploadFile
# pymupdf.pro.unlock()
from docx import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.table import Table
from comtypes.client import CreateObject
import mammoth


class FileProcessUseCase:
    def __init__(self):
        pass

    async def get_markdown_with_pymupdf4llm(self, file: UploadFile):
        try:
            filename = file.filename.lower()
            file_bytes = await file.read()
            file_stream = BytesIO(file_bytes)

            if filename.endswith(".pdf"):
                doc = fitz.open(stream=file_stream, filetype="pdf")
                return pymupdf4llm.to_markdown(doc)
            elif filename.endswith(".docx"):
                return await self._convert_docx_to_markdown(file_stream)
            elif filename.endswith(".doc"):
                doc_to_docx = await self.convert_doc_to_docx_bytesio(file_stream)
                return await self._convert_docx_to_markdown(doc_to_docx)
            else:
                raise ValueError("Unsupported file type. Only PDF, DOCX and DOC are supported.")
        except Exception as e:
            raise RuntimeError(f"Failed to parse file: {e}")

    async def _convert_docx_to_markdown(self, file_stream: BytesIO) -> str:
        doc = DocxDocument(file_stream)
        markdown_lines = []

        for block in doc.element.body:
            if block.tag.endswith('tbl'):  # 表格處理
                table = Table(block, doc)
                markdown_lines.append(await self._table_to_markdown(table))
            elif block.tag.endswith('p'):
                para = Paragraph(block, doc)
                markdown_lines.append(await self._paragraph_to_markdown(para))

        return "\n".join(markdown_lines)

    async def _paragraph_to_markdown(self, paragraph: Paragraph) -> str:
        text = ""
        for run in paragraph.runs:
            run_text = run.text
            if run.bold:
                run_text = f"**{run_text}**"
            if run.italic:
                run_text = f"*{run_text}*"
            text += run_text

        style = paragraph.style.name.lower()
        if "heading 1" in style:
            return f"# {text}"
        elif "heading 2" in style:
            return f"## {text}"
        elif "heading 3" in style:
            return f"### {text}"
        elif style.startswith("list"):
            return f"- {text}"
        return text

    async def _table_to_markdown(self, table: Table) -> str:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            rows.append(cells)

        if not rows:
            return ""

        # 轉為 Markdown 表格格式
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        content = ["| " + " | ".join(row) + " |" for row in rows[1:]]

        return "\n".join([header, separator] + content)

    async def convert_doc_to_docx_bytesio(self, input_stream: io.BytesIO) -> io.BytesIO:
        # 1. 先將 BytesIO 寫入暫存 doc 檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp_doc:
            tmp_doc.write(input_stream.read())
            tmp_doc_path = tmp_doc.name

        # 2. 用 Word COM 轉 doc -> docx
        word = CreateObject("Word.Application")
        doc = word.Documents.Open(tmp_doc_path)
        tmp_docx_path = tmp_doc_path + "x"
        doc.SaveAs(tmp_docx_path, 12)  # 12 = wdFormatDocumentDefault (.docx)
        doc.Close()
        word.Quit()

        # 3. 讀 docx 檔案內容為 BytesIO
        with open(tmp_docx_path, "rb") as docx_file:
            docx_bytes = docx_file.read()

        # 4. 清理暫存檔案
        os.remove(tmp_doc_path)
        os.remove(tmp_docx_path)

        # 5. 回傳 docx BytesIO（output stream）
        output_stream = io.BytesIO(docx_bytes)
        output_stream.seek(0)
        return output_stream
