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

load_dotenv('app/conf/.env')
os.environ['TIKTOKEN_CACHE_DIR'] = os.getenv('CL100K_BASE')

class RAGUseCase:
    def __init__(self):
        # self.agent_object = RAGAgent(index_name=os.getenv('AS_INDEX_NAME'), document_type="chunk")
        self.embedding = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv('EMBEDDING_MODEL'),
            openai_api_version=os.getenv('EMBEDDING_API_VERSION'),
            azure_endpoint=os.getenv('EMBEDDING_ENDPOINT'),
            api_key=os.getenv('EMBEDDING_API_KEY'),
        )
        # self._vector_store: Optional[AzureSearch] = None
        self._vector_store = AzureSearch(
            azure_search_endpoint=os.getenv('AS_ENDPOINT'),
            azure_search_key=os.getenv('AS_API_KEY'),
            index_name=os.getenv('AS_INDEX_NAME'),
            embedding_function=self.embedding.embed_query,
            semantic_configuration_name="my-semantic-config",
        )

    # @property
    # def vector_store(self) -> AzureSearch:
    #     if self._vector_store is None:
    #         self._vector_store = AzureSearch(
    #             azure_search_endpoint=os.getenv('AS_ENDPOINT'),
    #             azure_search_key=os.getenv('AS_API_KEY'),
    #             index_name=os.getenv('AS_INDEX_NAME'),
    #             embedding_function=self.embedding.embed_query,
    #             semantic_configuration_name="my-semantic-config",
    #         )
    #     return self._vector_store

    def run_rag_flow(self, question: str, top_k: int, score_threshold: float):
        """
        Execute entire RAG process, return top-1 similarity file(id) list based on input question.

        :param question: input question from user
        :return: get top-3 similarity file(id) list
        """
        if not (1 <= top_k <= 10000):
            logger.error(f"Invalid top_k value: {top_k}")
            return None
        try:
            documents = self.retrieve_documents_with_score(question, "similarity", -1, top_k, score_threshold)

            if not documents:
                logger.warning("No relevant documents found.")
                return None

            documents_as_dicts = [
                doc.metadata for doc in documents
            ]
            logger.info(f"Retrieved {len(documents_as_dicts)} documents")
            return documents_as_dicts
        except Exception as e:
            logger.error(f"Error in run_rag_flow: {str(e)}")
            return None

    def retrieve_documents_with_top_k(self, question: str, search_type: str, file_id: int, top_k: int) -> List[Document]:
        # search_type: "similarity", "hybrid", "semantic_hybrid"
        search_option = {
            # "top_k": top_k,
            "search_type": search_type,
        }

        if file_id != -1:
            search_option["filters"] = f"file_id eq {file_id}"

        # retriever = vector_store.as_retriever(search_kwargs=search_option, k=top_k)
        documents = self._vector_store.similarity_search(query=question,k=top_k)
        # documents = retriever.invoke(question)
        return documents

    def retrieve_documents_with_score(
            self,
            question: str,
            search_type: str = "similarity",
            file_id: int = -1,
            top_k: int = 10,
            score_threshold: float = 0.1
    ) -> List[Document]:
        filters = f"file_id eq {file_id}" if file_id != -1 else None
        logger.info(f"qusetion: {question}")
        # if search_type == "similarity":
        #     results = self.vector_store.similarity_search_with_score(query=question, k=top_k)
        # elif search_type == "hybrid":
        #     results = self.vector_store.hybrid_search_with_score(query=question, k=top_k, filters=filters)
        # elif search_type == "semantic_hybrid":
        #     results = self.vector_store.semantic_hybrid_search_with_score(query=question, k=top_k, filters=filters)
        # else:
        #     raise ValueError(f"Unknown search_type: {search_type}")
        # results = self._vector_store.similarity_search_with_score(query=question, k=top_k)
        try:
            results = self._vector_store.similarity_search_with_score(query=question, k=top_k)
        except Exception as e:
            logger.error(f"Error calling similarity_search_with_score: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            raise

        # 篩選符合 score 門檻的結果
        filtered_docs = [doc for doc, score in results if score >= score_threshold]
        return filtered_docs

    def get_documents_from_ais(
            self,
            question: str, file_id: int, top_k: int, score_threshold: float) -> List[Document]:
        return self.retrieve_documents_with_score(question, "semantic_hybrid", file_id, top_k, score_threshold)

    def get_provided_content(self, question: str, file_id: int, top_k: int, score_threshold: float) -> str:
        documents = self.retrieve_documents_with_score(question, "semantic_hybrid", file_id, top_k, score_threshold)
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
