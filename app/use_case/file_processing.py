import pymupdf4llm
from io import BytesIO
import fitz  # PyMuPDF
# from pymupdf4llm.helpers.pymupdf_rag import extract_markdown_from_doc
# import pymupdf.pro
from fastapi import UploadFile
# pymupdf.pro.unlock()
from docx import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.table import Table


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
            else:
                raise ValueError("Unsupported file type. Only PDF and DOCX are supported.")
        except Exception as e:
            raise RuntimeError(f"Failed to parse file via pymupdf4llm: {e}")

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
