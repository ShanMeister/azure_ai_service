import os
from typing import List
from dotenv import load_dotenv
from loguru import logger
# from src.doc2rag.rag import RAGAgent

from langchain_community.vectorstores.azuresearch import AzureSearch, Document
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureOpenAIEmbeddings

load_dotenv('conf/.env')

class RAGUseCase:
    def __init__(self):
        # self.agent_object = RAGAgent(index_name=os.getenv('AS_INDEX_NAME'), document_type="chunk")
        self.embedding = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv('EMBEDDING_MODEL'),
            openai_api_version=os.getenv('EMBEDDING_API_VERSION'),
            azure_endpoint=os.getenv('EMBEDDING_ENDPOINT'),
            api_key=os.getenv('EMBEDDING_API_KEY'),
        )
        self.vector_store = self.initialize_vector_store()
        pass

    def run_rag_flow(self, question: str, top_k: int):
        """
        Excute entire RAG process, retrun top-1 similarity file(id) list based on input question.

        :param question: input question from user
        :return: get top-3 similarity file(id) list
        """
        try:
            documents = self.retrieve_documents(self.vector_store, question, "semantic_hybrid", -1, top_k)

            if not documents:
                logger.warning("No relevant documents found.")
                return None
            print(documents)
            documents_as_dicts = [
                {"metadata": doc.metadata, "content": doc.page_content} for doc in documents
            ]
            logger.info(f"Retrieved {len(documents)} documents")
            print(documents_as_dicts)
            return documents_as_dicts
        except Exception as e:
            logger.error(f"Error in run_rag_flow: {str(e)}")
            return None

    def initialize_vector_store(self) -> AzureSearch:
        return AzureSearch(
            azure_search_endpoint=os.getenv('AS_ENDPOINT'),
            azure_search_key=os.getenv('AS_API_KEY'),
            index_name=os.getenv('AS_INDEX_NAME'),
            embedding_function=self.embedding.embed_query,
            semantic_configuration_name="my-semantic-config",
        )

    def retrieve_documents(
            self,
            vector_store: AzureSearch, question: str, search_type: str, file_id: int, top_k: int
    ) -> List[Document]:
        # search_type: "similarity", "hybrid", "semantic_hybrid"
        search_option = {
            # "top_k": top_k,
            "search_type": search_type,
        }

        if file_id != -1:
            search_option["filters"] = f"file_id eq {file_id}"

        # retriever = vector_store.as_retriever(search_kwargs=search_option, k=top_k)
        documents = vector_store.similarity_search(query=question,k=top_k)
        # documents = retriever.invoke(question)
        return documents

    def get_documents_from_ais(
            self,
            question: str, file_id: int, top_k: int
    ) -> List[Document]:
        vector_store = self.initialize_vector_store()
        return self.retrieve_documents(vector_store, question, "semantic_hybrid", file_id, top_k)

    def get_provided_content(
            self,
            question: str, file_id: int, top_k: int
    ) -> str:
        vector_store = self.initialize_vector_store()
        documents = self.retrieve_documents(
            vector_store, question, "semantic_hybrid", file_id, top_k
        )
        if not documents:
            return "No supporting information found."

        content_template_str = "\n".join(
            [
                f"**Ref {i + 1}**\n{{context{i + 1}}}\n\n"
                for i in range(min(len(documents), top_k))
            ]
        )
        content_template = PromptTemplate.from_template(content_template_str)

        context_data = {
            f"context{i + 1}": doc.page_content for i, doc in enumerate(documents)
        }
        result = content_template.invoke(context_data).text

        return result
