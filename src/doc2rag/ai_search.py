from typing import Generator, Union, List, Dict
from collections import defaultdict
from itertools import islice
from logging import Logger

import requests
from sqlalchemy.orm import Session
from langchain_openai import AzureOpenAIEmbeddings

from .db_utils.database import BaseSQLAgent
from .db_utils.models import File, Chunk, SplitFile
from .logger_utils import LoggingAgent
from .config_utils import (
    AzureAISearchConfig,
    EmbeddingConfig,
    TiktokenConfig,
    PathConfig,
)

TiktokenConfig().set_tiktoken_cache_dir_in_env("cl100k_base")


class CreateIndexError(Exception):
    pass


class UpdateFileStatusError(Exception):
    pass


# region Helper Functions
def group_chunks_by_index(
    chunks: List["Chunk"], file_ids: List[int], index_names: List[str]
) -> Dict[str, Dict[int, List["Chunk"]]]:
    """
    Groups chunks into a nested dictionary by index names and file IDs.

    Args:
        chunks (List['Chunk']): A list of chunks, where each chunk corresponds to a file.
        file_ids (List[int]): A list of file IDs corresponding to the chunks.
        index_names (List[str]): A list of index names corresponding to the chunks.

    Returns:
        Dict[str, Dict[int, List['Chunk']]]:
            Nested dictionary grouping chunks by index name and file ID.
    """
    grouped_data = defaultdict(lambda: defaultdict(list))

    for chunk, file_id, index_name in zip(chunks, file_ids, index_names):
        grouped_data[index_name][file_id].append(chunk)

    # Convert inner defaultdicts to regular dicts for immutability and clarity.
    return {index_name: dict(files) for index_name, files in grouped_data.items()}


def map_file_ids_to_names(file_ids: List[int], file_names: List[str]) -> Dict[int, str]:
    """
    Maps file IDs to their corresponding file names.

    Args:
        file_ids (List[int]): A list of file IDs.
        file_names (List[str]): A list of file names.

    Returns:
        Dict[int, str]: Dictionary mapping file IDs to file names.
    """
    return dict(zip(file_ids, file_names))


def batch_items(
    items: List[Chunk], batch_size=10
) -> Generator[List[Chunk], None, None]:
    iterator = iter(items)
    for first in iterator:
        yield list(islice(iterator, batch_size - 1)) + [first]


def check_with_user_about_index_name(
    endpoint: str, index_name: str, action: str
) -> bool:
    """
    Check with the user if the index name is correct and if they want to proceed with the action.

    Args:
        index_name (str): The index name to be checked.
        action (str): The action to be performed.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    print(f"Endpoint: {endpoint}")
    print(f"Index name: {index_name}")
    print(f"Action: {action}")
    response = input("Do you want to proceed? [y/n]: ")
    return response.lower() == "y"


# endregion


class IndexAgent:
    def __init__(self):
        self.logger = LoggingAgent("AzureAISearch").logger
        self.ais_config = AzureAISearchConfig()
        self.endpoint = self.ais_config.endpoint
        self.api_version = self.ais_config.api_version
        self.api_key = self.ais_config.api_key
        self.embed_dim = EmbeddingConfig().dimension
        self.index_list = PathConfig().index_list

    def create_indices(self):
        for index_name in self.index_list:
            try:
                self._create_index(index_name)
            except CreateIndexError as e:
                self.logger.error(f"Error creating index {index_name}: {e}")
            except Exception as e:
                self.logger.error(f"Error creating index {index_name}: {e}")

    def _create_index(self, index_name: str):
        """
        Create an index in Azure AI Search with the provided schema.

        Index name must only contain lowercase letters, digits or dashes, cannot start or end with dashes and is limited to 128 characters
        """
        if not check_with_user_about_index_name(
            self.endpoint, index_name, "create-index"
        ):
            self.logger.info("User cancelled the operation.")
            return
        url = f"{self.endpoint}/indexes?api-version={self.api_version}"
        try:
            response = requests.request(
                method="POST",
                url=url,
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.api_key,
                },
                json={
                    "name": index_name,
                    "fields": self.get_fields(),
                    "vectorSearch": self.get_vector_search_config(),
                    "semantic": self.get_semantic_search_config(),
                },
            )
            response.raise_for_status()
            self.logger.info(f"Index created successfully: {index_name}")
        except Exception as e:
            self.logger.error(f"Failed to create index: {e}")
            pass
            # raise CreateIndexError(
            #     f"Failed to create index: {e}\nResponse Error:\n{response.json()}"
            # )

    def delete_index(self):
        """
        Delete the index in Azure AI Search.
        """
        raise NotImplementedError("This method needs to be implemented.")

    def get_fields(self):
        fields = [
            {
                "name": "id",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,
                "sortable": True,
                "facetable": False,
                "key": True,
            },
            {
                "name": "document_type",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,
                "sortable": True,
                "facetable": False,
                "key": False,
            },
            {
                "name": "file_id",
                "type": "Edm.Int64",
                "searchable": False,
                "filterable": True,
                "retrievable": True,
                "sortable": True,
                "facetable": False,
                "key": False,
            },
            {
                "name": "file_name",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True,
                "sortable": True,
                "facetable": False,
                "key": False,
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "filterable": False,
                "retrievable": True,
                "sortable": False,
                "facetable": False,
                "key": False,
            },
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": True,
                "dimensions": self.embed_dim,
                "vectorSearchProfile": "my-vector-profile",
            },
        ]
        return fields

    def get_vector_search_config(self):
        vector_search_config = {
            "algorithms": [
                {
                    "name": "my-hnsw-config",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine",
                    },
                },
                {
                    "name": "my-eknn-config",
                    "kind": "exhaustiveKnn",
                    "exhaustiveKnnParameters": {"metric": "cosine"},
                },
            ],
            "profiles": [{"name": "my-vector-profile", "algorithm": "my-hnsw-config"}],
        }
        return vector_search_config

    def get_semantic_search_config(self):
        semantic_search_config = {
            "configurations": [
                {
                    "name": "my-semantic-config",
                    "prioritizedFields": {
                        "prioritizedContentFields": [{"fieldName": "content"}],
                    },
                }
            ]
        }
        return semantic_search_config


class IndexUploadAgent:

    def __init__(
        self,
        logger: Logger,
        index_name: str,
        files: Dict[int, List[Chunk]],
        file_id_to_name: Dict[int, str],
        batch_size: int = 10,
        retry_attempts: int = 3,
    ) -> None:
        self.logger = logger
        self.index_name = index_name
        self.files = files
        self.file_id_to_name = file_id_to_name
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts

        self._url = None
        self._headers = None
        self._embedding = None

        self.document_type = "Chunk"  # Default to Chunk; update as needed

    def initialize(
        self, ais_config: AzureAISearchConfig, embed_config: EmbeddingConfig
    ) -> None:
        self._set_url(ais_config.endpoint, ais_config.api_version)
        self._set_headers(ais_config.api_key)
        self._set_embedding(embed_config)

    def upload_chunks(self, session: Session) -> None:
        for file_id, chunks in self.files.items():
            file_name = self.file_id_to_name[file_id]
            try:
                self._upload(session, chunks, file_id, file_name)
                self._update_file_status(session, file_id, "uploaded")
                self.logger.info(f"File {file_id} uploaded successfully.")
            except UpdateFileStatusError as e:
                self.logger.error(f"Error uploading file {file_id}: {e}")
            except Exception as e:
                self.logger.error(f"Error uploading file {file_id}: {e}")
                self._update_file_status(session, file_id, "upload-failed")

    def _upload(
        self, session: Session, items: List[Chunk], file_id: int, file_name: str
    ) -> None:
        """
        Upload items to the specified URL.

        Args:
            items (List['Chunk']): A list of items to be uploaded.
            file_id (int): The ID of the file containing the items.
            file_name (str): The name of the file containing the items.
        """
        total_batches = (
            len(items) + self.batch_size - 1
        ) // self.batch_size  # Calculate total number of batches
        batch_count = 0

        for batch in batch_items(items, batch_size=self.batch_size):
            batch_count += 1
            self.logger.info(
                f"Starting upload for batch {batch_count}/{total_batches}..."
            )

            payload = self._prepare_payload(batch, file_id, file_name)
            if not payload["value"]:
                self.logger.warning(
                    f"No valid {self.document_type.lower()}s in batch {batch_count}. Skipping upload."
                )
                continue

            success = False
            for attempt in range(1, self.retry_attempts + 1):  # Retry logic
                self.logger.info(f"Attempt {attempt} for batch {batch_count}...")
                if self._post_payload(payload):
                    self._mark_uploaded(batch, session)
                    success = True
                    break
                else:
                    self.logger.error(
                        f"Failed to upload batch {batch_count}. Retrying..."
                    )

            if success:
                self.logger.info(
                    f"Successfully uploaded for (file_id = {file_id}, file_name = {file_name}, batch = {batch_count})"
                )
            else:
                self.logger.error(
                    f"Exhausted retries for (file_id = {file_id}, file_name = {file_name}, batch = {batch_count})"
                )

    def _set_url(self, endpoint: str, api_version: str):
        self._url = f"{endpoint}/indexes('{self.index_name}')/docs/search.index?api-version={api_version}"

    def _set_headers(self, api_key: str):
        self._headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }

    def _set_embedding(self, embed_config: EmbeddingConfig):
        self._embedding = AzureOpenAIEmbeddings(
            azure_deployment=embed_config.deployment,
            openai_api_version=embed_config.api_version,
            azure_endpoint=embed_config.endpoint,
            api_key=embed_config.api_key,
        )

    def _update_file_status(self, session: Session, file_id: int, status: str):
        """
        Update the statuses of multiple files in one database operation.
        """
        file: Union[File, None] = session.query(File).get(file_id)
        if not file:
            raise UpdateFileStatusError(f"File {file_id} not found in the database.")
        file.status = status
        session.commit()

    def _prepare_payload(
        self, batch: List[Chunk], file_id: int, file_name: str
    ) -> dict:
        """
        Prepare the payload for uploading a batch of items.

        Args:
            batch (List['Chunk']): A list of items to be uploaded.
            file_id (int): The ID of the file containing the items.
            file_name (str): The name of the file containing the items.
        """
        return {
            "value": [
                {
                    "@search.action": "upload",
                    "id": chunk.ai_search_id,
                    "document_type": self.document_type,
                    "file_id": file_id,
                    "file_name": file_name,
                    "content": chunk.content,
                    "content_vector": self._embedding.embed_query(chunk.content),
                }
                for chunk in batch
            ]
        }

    def _post_payload(self, payload: dict) -> bool:
        try:
            response = requests.post(self._url, json=payload, headers=self._headers)
            if response.status_code == 200:
                return True
            else:
                self.logger.error(
                    f"Failed to upload chunks: {response.status_code}, {response.text}"
                )
                return False
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")

    def _mark_uploaded(self, batch: List[Chunk], session: Session) -> None:
        """Mark items as uploaded in the database."""
        try:
            for item in batch:
                item.status = "uploaded"
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(
                f"Error updating {self.document_type.lower()} statuses: {str(e)}"
            )


class UploadController:
    """
    Main interface for CLI to upload chunks to Azure AI Search.
    """

    def __init__(self, sql_agent: BaseSQLAgent) -> None:
        self.logger = LoggingAgent(f"AzureAISearch").logger
        self.SessionLocal = sql_agent.SessionLocal

        self._ais_config = AzureAISearchConfig()
        self._embed_config = EmbeddingConfig()

    def upload(self):
        with self.SessionLocal() as session:
            chunks, file_ids, file_names, index_names = self._fetch_chunks_to_upload(
                session
            )
            grouped_data = group_chunks_by_index(chunks, file_ids, index_names)
            file_id_to_name = map_file_ids_to_names(file_ids, file_names)
            for index_name, files in grouped_data.items():
                agent = IndexUploadAgent(
                    self.logger, index_name, files, file_id_to_name
                )
                agent.initialize(self._ais_config, self._embed_config)
                agent.upload_chunks(session)

    def _fetch_chunks_to_upload(
        self, session: Session
    ) -> tuple[list[Chunk], list[int], list[str], list[str]]:
        """
        Retrieve only the fields necessary for upload.

        Returns:
            chunks (List['Chunk']): A list of chunks, where each chunk corresponds to a file.
            file_ids (List[int]): A list of file IDs corresponding to the chunks.
            file_names (List[str]): A list of file names corresponding to the file IDs.
            index_names (List[str]): A list of index names corresponding to the chunks.
        """
        results = (
            session.query(
                Chunk,
                File.id.label("file_id"),
                File.name.label("file_name"),
                File.index_name.label("index_name"),
            )
            .join(SplitFile, Chunk.split_file_id == SplitFile.id)
            .join(File, SplitFile.file_id == File.id)
            .filter(Chunk.status == "wait-for-upload")
            .all()
        )
        chunks, file_ids, file_names, index_names = (
            zip(*results) if results else ([], [], [], [])
        )
        return chunks, file_ids, file_names, index_names


class IndexDeleteAgent:

    def __init__(
        self,
        logger: Logger,
        index_name: str,
        files: Dict[int, List[Chunk]],
        file_id_to_name: Dict[int, str],
        batch_size: int = 10,
        retry_attempts: int = 3,
    ) -> None:
        self.logger = logger
        self.index_name = index_name
        self.files = files
        self.file_id_to_name = file_id_to_name
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts

        self._url = None
        self._headers = None

    def initialize(self, ais_config: AzureAISearchConfig) -> None:
        self._url = f"{ais_config.endpoint}/indexes('{self.index_name}')/docs/search.index?api-version={ais_config.api_version}"
        self._headers = {
            "Content-Type": "application/json",
            "api-key": ais_config.api_key,
        }

    def delete_chunks(self, session: Session) -> None:
        for file_id, chunks in self.files.items():
            try:
                self._process_deletion(session, chunks)
                self.logger.info(f"Successfully deleted chunks for File(id={file_id}).")
            except Exception as e:
                self.logger.error(f"Error deleting file {file_id}: {e}")

    def _process_deletion(self, session: Session, items: List[Chunk]) -> None:
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        for batch_count, batch in enumerate(
            batch_items(items, self.batch_size), start=1
        ):
            self.logger.info(f"Deleting batch {batch_count}/{total_batches}...")
            payload = self._create_payload(batch)

            if not payload["value"]:
                self.logger.warning(
                    f"No valid chunks in batch {batch_count}. Skipping."
                )
                continue

            success = self._retry_deletion(payload, batch, session, batch_count)
            if success:
                self.logger.info(f"Batch {batch_count} deleted successfully.")
            else:
                self.logger.error(
                    f"Failed to delete batch {batch_count} after retries."
                )

    def _create_payload(self, batch: List[Chunk]) -> dict:
        try:
            return {
                "value": [
                    {"@search.action": "delete", "id": chunk.ai_search_id}
                    for chunk in batch
                ]
            }
        except Exception as e:
            self.logger.error(f"Error creating payload: {e}")
            return {"value": []}

    def _retry_deletion(
        self, payload: dict, batch: List[Chunk], session: Session, batch_count: int
    ) -> bool:
        for attempt in range(1, self.retry_attempts + 1):
            self.logger.info(f"Attempt {attempt} for batch {batch_count}...")
            if self._post_payload(payload):
                self._update_chunk_status(batch, session)
                return True
            self.logger.error(f"Attempt {attempt} failed for batch {batch_count}.")
        return False

    def _post_payload(self, payload: dict) -> bool:
        try:
            response = requests.post(self._url, json=payload, headers=self._headers)
            if response.ok:
                return True
            self.logger.error(
                f"Request failed with status {response.status_code}: {response.text}"
            )
        except requests.RequestException as e:
            self.logger.error(f"Request error: {e}")
        return False

    def _update_chunk_status(self, batch: List[Chunk], session: Session) -> None:
        try:
            for chunk in batch:
                chunk.status = "deleted"
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating chunk statuses: {e}")


class DeleteController:
    def __init__(self, sql_agent: BaseSQLAgent) -> None:
        self.logger = LoggingAgent("AzureAISearch").logger
        self.SessionLocal = sql_agent.SessionLocal
        self._ais_config = AzureAISearchConfig()

    def delete(self):
        with self.SessionLocal() as session:
            chunks, file_ids, file_names, index_names = self._fetch_chunks(session)
            grouped_data = group_chunks_by_index(chunks, file_ids, index_names)
            file_id_to_name = map_file_ids_to_names(file_ids, file_names)

            for index_name, files in grouped_data.items():
                agent = IndexDeleteAgent(
                    self.logger, index_name, files, file_id_to_name
                )
                agent.initialize(self._ais_config)
                agent.delete_chunks(session)

    def _fetch_chunks(
        self, session: Session
    ) -> tuple[list[Chunk], list[int], list[str], list[str]]:
        results = (
            session.query(
                Chunk,
                File.id.label("file_id"),
                File.name.label("file_name"),
                File.index_name.label("index_name"),
            )
            .join(SplitFile, Chunk.split_file_id == SplitFile.id)
            .join(File, SplitFile.file_id == File.id)
            .filter(Chunk.status == "wait-for-delete")
            .all()
        )
        return zip(*results) if results else ([], [], [], [])
