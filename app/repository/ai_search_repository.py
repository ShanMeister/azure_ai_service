import os
from typing import List
from loguru import logger
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv('app/conf/.env')

class AISearchRepository:
    def __init__(self):
        self.search_endpoint = os.getenv("AS_ENDPOINT")
        self.index_name = os.getenv("AS_INDEX_NAME")
        self.api_key = os.getenv("AS_API_KEY")

        self.embedding_client = AsyncAzureOpenAI(
            api_key=os.getenv("EMBEDDING_API_KEY"),
            api_version=os.getenv("EMBEDDING_API_VERSION"),
            azure_endpoint=os.getenv("EMBEDDING_ENDPOINT"),
        )
        self.embedding_model = os.getenv("EMBEDDING_MODEL")

    async def __aenter__(self):
        """Enter the context of using the repository, create the client session."""
        self.client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.api_key),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and close the client session."""
        await self.client.close()

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text using the embedding client."""
        try:
            response = await self.embedding_client.embeddings.create(
                input=[text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.exception("Embedding generation failed")
            return []

    async def upload_document(self, doc: dict):
        """Upload a single document to Azure Search."""
        try:
            doc['content_vector'] = await self.generate_embedding(doc["content"])
            doc['@search.action'] = 'upload'
            result = await self.client.upload_documents(documents=[doc])
            logger.info(f"Uploaded document result to Azure Search: {result}")
        except Exception as e:
            logger.exception("Upload document to Azure Search failed")

    async def upload_documents_bulk(self, docs: List[dict]):
        """Upload multiple documents to Azure Search in bulk."""
        try:
            for doc in docs:
                doc['content_vector'] = await self.generate_embedding(doc["content"])
                doc['@search.action'] = 'upload'
            result = await self.client.upload_documents(documents=docs)
            logger.info(f"Bulk upload result to Azure Search: {result}")
        except Exception as e:
            logger.exception("Bulk upload to Azure Search failed")

    async def delete_document(self, id: str):
        """Delete a document from Azure Search by its id."""
        try:
            result = await self.client.delete_documents(documents=[{"id": id}])
            logger.info(f"Deleted document result from Azure Search: {result}")
        except Exception as e:
            logger.exception("Delete document from Azure Search failed")