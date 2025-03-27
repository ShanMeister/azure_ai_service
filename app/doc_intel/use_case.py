import os
import sys
from dotenv import load_dotenv
import io
from pathlib import Path
from logging import Logger
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
# from .repository.database import BaseSQLAgent
# from .repository.models import File
from loguru import logger
# from .utils.logger_utils import LoggingAgent
# from .utils.config_utils import PathConfig
# from .utils.pdf_utils import get_n_pages_from_pdf
# from .comtypes_converter import WORD2PDFAgent, PPT2PDFAgent, EXCEL2PDFAgent
# from .utils.config_utils import SQLTypeConfig
from .preprocessing.file_split import FileSplitter

from app.enums.action_enum import ActionEnum

class PDFUseCase:
    """
    Scans directories and processes PDF files based on their `process_type`.
    """

    def __init__(self):
        """
        Initialize the PDFScanner with required configurations.

        :param sql_agent: SQL agent for database operations.
        """
        pass
        # sql_agent = BaseSQLAgent
        # self.SessionLocal = sql_agent.SessionLocal
        # self.logger = LoggingAgent("PDFUseCase").logger

    def process_summarize_file(self, file, filename: str, text: str, action: ActionEnum) -> str:
        try:
            logger.info(f"Starting to process file: {filename}")
            # sql_agent = SQLAgent()
            FileSplitter().process_files(file)

            # DIProcessor(sql_agent).run()
            # SplitFilesProcessor(sql_agent).run()
            # FigureDescriptionGenerator(sql_agent).generate()
            # TextTableImageBundler(sql_agent).bundle()
            logger.info(f"Completed processing for file: {filename}")
            return "Processing completed successfully."

        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {e}")
            return "Error processing the PDF."




# class WORDScanner(BaseOfficeScanner):
#     def __init__(self):
#         super().__init__(file_extension="doc", agent_class=WORD2PDFAgent)
#
#
# class PPTScanner(BaseOfficeScanner):
#     def __init__(self):
#         super().__init__(file_extension="ppt", agent_class=PPT2PDFAgent)
#
#
# class EXCELScanner(BaseOfficeScanner):
#     def __init__(self):
#         super().__init__(file_extension="xls", agent_class=EXCEL2PDFAgent)
