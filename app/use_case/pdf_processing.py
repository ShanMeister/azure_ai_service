import os
import time
import httpx
import asyncio
from dotenv import load_dotenv
from loguru import logger
import fitz  # PyMuPDF
from fastapi import UploadFile
from app.repository.azure_services import AzureDocumentIntelligenceRepository
from app.enums.action_enum import ActionEnum


class PDFProcessingUseCase:
    def __init__(self):
        self.azure_doc_intel = AzureDocumentIntelligenceRepository()
        # self.azure_llm = AzureLLM()

    async def process_pdf(self, file: UploadFile, action: ActionEnum):
        pdf_document = fitz.open(stream=await file.read(), filetype="pdf")
        markdown_pages = []

        for page_num in range(len(pdf_document)):
            page_text = pdf_document[page_num].get_text("text")
            markdown_text = await self.azure_doc_intel.extract_markdown(page_text)
            markdown_pages.append(markdown_text)

        full_markdown = "\n\n".join(markdown_pages)
        result = await self.azure_llm.process_text(full_markdown, action)

        return result
