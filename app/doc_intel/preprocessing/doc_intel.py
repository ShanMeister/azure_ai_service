from typing import Union
import pickle
import io
from pathlib import Path
import time
from logging import Logger

from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentContentFormat
from azure.ai.documentintelligence import AnalyzeDocumentLROPoller
from sqlalchemy.orm import Session, joinedload

from ..repository.models import SplitFile, DIRequest
from ..repository.database import BaseSQLAgent
from ..utils.logger_utils import LoggingAgent
from ..utils.config_utils import PathConfig, DocumentIntelligenceConfig
from ..utils.time_utils import get_current_time


class DIError(Exception):
    pass


class PollerDict(BaseModel):
    filename: str
    poller: AnalyzeDocumentLROPoller
    waiting_time: int  # in seconds
    split_file: SplitFile
    di_request: DIRequest

    class Config:
        arbitrary_types_allowed = True


class Submitter:
    """
    Submitter handles the logic for submitting jobs to the Document Intelligence service.

    It validates files, submits them for processing, and registers their requests in the database.

    Attributes:
        client (DocumentIntelligenceClient): Azure client for interacting with the Document Intelligence service.
        logger (logging.Logger): Logger instance for logging job submission activities.
        path_config (PathConfig): Configuration for directory paths.

    Methods:
        submit_jobs(session, split_files, interval, pollers):
            Submits a batch of files for processing, with a delay between each submission.
        _submit_single_job(session, split_file, pollers):
            Submits an individual file for processing and updates the database.
        _get_file_path_and_validate(session, split_file):
            Validates the existence of the file to be submitted.
        _update_split_file_status(session, split_file, status):
            Updates the processing status of a split file in the database.
        _register_di_request(session, split_file_id):
            Registers a DI request in the database for a specific split file.
        _convert_pdf_to_iobytes(file_path):
            Converts a PDF file into a binary stream for submission.
    """

    def __init__(
        self,
        client: DocumentIntelligenceClient,
        logger: Logger,
        path_config: PathConfig,
        interval: int,
    ):
        """
        Initialize the Submitter.

        Args:
            client (DocumentIntelligenceClient): Azure client for interacting with the Document Intelligence service.
            logger (logging.Logger): Logger instance for logging job submission activities.
            path_config (PathConfig): Configuration for directory paths.
            interval (int): Interval (in seconds) between job submissions.
        """
        self.client = client
        self.logger = logger
        self.path_config = path_config
        self.interval = interval

    def submit_jobs(
        self,
        session: Session,
        split_files: list[SplitFile],
        pollers: list,
    ):
        """Submit jobs to the Document Intelligence service."""
        for split_file in split_files:
            self._submit_single_job(session, split_file, pollers)
            time.sleep(self.interval)

    def _submit_single_job(
        self, session: Session, split_file: SplitFile, pollers: list
    ):
        try:
            file_path = self._get_file_path_and_validate(session, split_file)
            if not file_path:
                return
            iobytes = self._convert_pdf_to_iobytes(pdf_bytes)
            pages = self._get_pages(split_file)
            poller = self.client.begin_analyze_document(
                "prebuilt-layout",
                iobytes,
                content_type="application/pdf",
                output_content_format=DocumentContentFormat.MARKDOWN,
                pages=pages,
            )
            split_file_name = self._get_split_file_name(split_file)
            di_request = self._register_di_request(session, split_file.id)
            pollers.append(
                PollerDict(
                    filename=split_file_name,
                    poller=poller,
                    waiting_time=0,
                    split_file=split_file,
                    di_request=di_request,
                )
            )
            self.logger.info(
                f"Submitted ({split_file.file.name}, {split_file_name}) for analysis."
            )
            self._update_split_file_status(session, split_file, "di-processing")
        except Exception as e:
            self.logger.error(
                f"Failed to submit SplitFileID {split_file_name}: {e}", exc_info=True
            )

    def _get_file_path_and_validate(
        self, session: Session, split_file: SplitFile
    ) -> Union[Path, None]:
        file_path = (
            self.path_config.get_split_dir_path(split_file.file.file_dir_name)
            / f"{split_file.split_id}.pdf"
        )
        if not file_path.exists():
            self.logger.error(f"File {file_path} does not exist.")
            self._update_split_file_status(session, split_file, "failed")
            return None
        return file_path

    def _get_pages(self, split_file: SplitFile) -> str:
        """
        Range of 1-based page numbers to analyze.  Ex. "1-3,5,7-9".
        """
        if split_file.n_pages == 1:
            return "1"
        else:
            return f"1-{split_file.n_pages}"

    def _update_split_file_status(
        self, session: Session, split_file: SplitFile, status: str
    ):
        split_file.status = status
        session.commit()

    def _register_di_request(self, session: Session, split_file_id: int) -> DIRequest:
        di_request = DIRequest(
            request_at=get_current_time(), split_file_id=split_file_id
        )
        session.add(di_request)
        session.commit()
        return di_request

    def _convert_pdf_to_iobytes(self, pdf_bytes: bytes) -> io.BytesIO:
        return io.BytesIO(pdf_bytes)
    # def _convert_pdf_to_iobytes(self, file_path: Path) -> io.BytesIO:
    #     with open(file_path, "rb") as f:
    #         return io.BytesIO(f.read())

    def _get_split_file_name(self, split_file: SplitFile) -> str:
        return f"{split_file.split_id}.pdf"


class Listener:
    """
    Listener monitors the status of jobs submitted to the Document Intelligence service.

    It polls for job completion, handles results, and updates the database based on job outcomes.

    Attributes:
        client (DocumentIntelligenceClient): Azure client for interacting with the Document Intelligence service.
        logger (logging.Logger): Logger instance for logging job listening activities.
        path_config (PathConfig): Configuration for directory paths.
        check_period (int): Time (in seconds) between polling cycles.
        max_wait_time (int): Maximum allowed time (in seconds) for a job to complete.

    Methods:
        listen_jobs(session, pollers):
            Polls for job status and processes results until all jobs are completed.
        _process_polling(session, poller_dict, pollers):
            Processes the polling status of an individual job and handles timeouts or completion.
        _handle_completed_poll(session, poller_dict):
            Handles successful or failed jobs and updates the database accordingly.
        _save_result_to_file(poller, file_path):
            Saves the job result to a pickle file on disk.
        _update_status(session, poller_dict, status):
            Updates the status of the DI request and split file in the database.
    """

    def __init__(
        self,
        client: DocumentIntelligenceClient,
        logger: Logger,
        path_config: PathConfig,
        check_period: int,
        max_wait_time: int,
    ):
        """
        Initialize the Listener.

        Args:
            client (DocumentIntelligenceClient): Azure client for interacting with the Document Intelligence service.
            logger (logging.Logger): Logger instance for logging job listening activities.
            path_config (PathConfig): Configuration for directory paths.
            check_period (int): Time (in seconds) between polling cycles.
            max_wait_time (int): Maximum allowed time (in seconds) for a job to complete.
        """
        self.client = client
        self.logger = logger
        self.path_config = path_config
        self.check_period = check_period
        self.max_wait_time = max_wait_time

    def listen_jobs(self, session: Session, pollers: list):
        """
        Polls for job status and processes results until all jobs are completed.
        """
        while pollers:
            for poller_dict in pollers[:]:
                self._process_polling(session, poller_dict, pollers)
            if pollers:
                self.logger.info(
                    f"Waiting {self.check_period} seconds before next poll."
                )
                time.sleep(self.check_period)
        self.logger.info("All jobs completed.")

    def _process_polling(
        self, session: Session, poller_dict: PollerDict, pollers: list
    ):
        poller = poller_dict.poller
        filename = poller_dict.filename
        if poller.done():
            self._handle_completed_poll(session, poller_dict)
            pollers.remove(poller_dict)
        else:
            poller_dict.waiting_time += self.check_period
            if poller_dict.waiting_time > self.max_wait_time:
                self.logger.warning(f"Job {filename} exceeded max waiting time.")
                pollers.remove(poller_dict)
                self._update_status(
                    session, poller_dict, "di-failed", "over-max-wait-time"
                )

    def _handle_completed_poll(self, session: Session, poller_dict: PollerDict):
        poller = poller_dict.poller
        split_file = poller_dict.split_file
        pkl_name = f"{split_file.split_id}.pkl"
        output_path = (
            self.path_config.get_pkl_dir_path(split_file.file.file_dir_name) / pkl_name
        )

        if poller.status().lower() == "succeeded":
            self.logger.info(f"Job {output_path} succeeded.")
            self._save_result_to_file(poller, output_path)
            self._update_status(session, poller_dict, "di-success", "success")
        else:
            self.logger.warning(
                f"Job {output_path} failed with status: {poller.status()}."
            )
            self._update_status(session, poller_dict, "di-failed", "failed")

    def _save_result_to_file(self, poller: AnalyzeDocumentLROPoller, file_path: Path):
        try:
            result: AnalyzeResult = poller.result()
            with open(file_path, "wb") as f:
                pickle.dump(result, f)
        except Exception as e:
            self.logger.error(
                f"Failed to save result to {file_path}: {e}", exc_info=True
            )

    def _update_status(
        self,
        session: Session,
        poller_dict: PollerDict,
        sf_status: str,
        di_status: str,
    ):
        di_request = poller_dict.di_request
        split_file = poller_dict.split_file
        di_request.status = di_status
        di_request.finish_at = get_current_time()
        split_file.status = sf_status
        session.commit()


class DIProcessor:
    """
    DIProcessor orchestrates the workflow for processing files with the Document Intelligence service.

    It manages the submission of jobs, monitors their completion, and coordinates the activities
    of the Submitter and Listener classes.

    Attributes:
        SessionLocal (callable): A factory for database session objects.
        path_config (PathConfig): Configuration for directory paths.
        pollers (list[PollerDict]): A list to track jobs and their pollers.
        submitter (Submitter): Handles job submission to the Document Intelligence service.
        listener (Listener): Monitors job status and handles completion.
        end_flag (bool): A flag to terminate the main loop.
    """

    def __init__(
        self,
        sql_agent: BaseSQLAgent,
    ):
        """
        Initialize the DIProcessor.

        Args:
            sql_agent (BaseSQLAgent): An instance of BaseSQLAgent.
        """
        self.logger = LoggingAgent("DIProcessor").logger
        self.SessionLocal = sql_agent.SessionLocal
        self.path_config = PathConfig()
        self.pollers: list[PollerDict] = []

        doc_intel_config = DocumentIntelligenceConfig()
        client = DocumentIntelligenceClient(
            endpoint=doc_intel_config.endpoint,
            credential=AzureKeyCredential(doc_intel_config.api_key),
            api_version=doc_intel_config.api_version,
        )
        self.submit_interval = doc_intel_config.submit_interval
        self.check_period = doc_intel_config.check_period
        self.max_wait_time = doc_intel_config.max_wait_time
        self.batch_size = doc_intel_config.batch_size
        self.main_loop_wait = doc_intel_config.main_loop_wait

        self.submitter = Submitter(
            client, self.logger, self.path_config, self.submit_interval
        )

        self.listener = Listener(
            client, self.logger, self.path_config, self.check_period, self.max_wait_time
        )
        self.end_flag = False

    def run(self):
        with self.SessionLocal() as session:
            while not self.end_flag:
                # split_files = self._fetch_split_files_to_analyze(session)
                if not split_files:
                    self.logger.info("No files to analyze.")
                    self.end_flag = True
                    break
                self.submitter.submit_jobs(session, split_files, self.pollers)
                self.listener.listen_jobs(session, self.pollers)
                self.logger.info(
                    f"Waiting {self.main_loop_wait} seconds before next iteration to process remaining SplitFiles."
                )
                time.sleep(self.main_loop_wait)

    # def _fetch_split_files_to_analyze(self, session: Session) -> list[SplitFile]:
    #     return (
    #         session.query(SplitFile)
    #         .filter(SplitFile.status == "wait-for-di")
    #         .options(joinedload(SplitFile.file))  # Load the related File object
    #         .limit(self.batch_size)
    #         .all()
    #     )
