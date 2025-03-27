from typing import List

from langchain_community.vectorstores.azuresearch import AzureSearch, Document
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

from .logger_utils import LoggingAgent
from .config_utils import (
    AzureOpenAIConfig,
    EmbeddingConfig,
    AzureAISearchConfig,
)


DEFAULT_SYS_PROMPT_RAG = """You are a friendly AI Assistant! Your role is to answer questions using only the provided information. If possible, include the source where the answer can be found. If the content contains tables or code, format the output in Markdown. {context}"""


class RAGAgent:

    def __init__(self, index_name: str = None, document_type: str = "Chunk") -> None:
        self.logger = LoggingAgent("RAGAgent").logger
        self.llm = self._get_llm()
        self.document_type = document_type  # "Chunk" or "Figure"

        if index_name is not None:
            self.index_name = index_name
            self.embedding = self._get_embedding()
            self.retriever = self._get_retriever()
            self.prompt = self._get_prompt()
            self.chain = self.prompt | self.llm | StrOutputParser()

    def _get_llm(self):
        config = AzureOpenAIConfig()
        return AzureChatOpenAI(
            azure_endpoint=config.endpoint,
            api_version=config.api_version,
            api_key=config.api_key,
            azure_deployment=config.deployment,
            temperature=0.5,
        )

    def _get_embedding(self):
        config = EmbeddingConfig()
        return AzureOpenAIEmbeddings(
            azure_deployment=config.deployment,
            openai_api_version=config.api_version,
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
        )

    def _get_retriever(self):
        config = AzureAISearchConfig()
        vector_store = AzureSearch(
            azure_search_endpoint=config.endpoint,
            azure_search_key=config.api_key,
            index_name=self.index_name,
            embedding_function=self.embedding.embed_query,
            semantic_configuration_name="my-semantic-config",
        )
        # search_type: "similarity" or "hybrid", "semantic_hybrid"
        return vector_store.as_retriever(
            search_type="semantic_hybrid",
            k=3,
        )

    def _get_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{system_prompt}\n{context}",
                ),
                ("human", "{question}"),
            ]
        )

    def get_documents(self, question: str) -> List[Document]:
        filters = f"document_type eq '{self.document_type}'"
        documents: List[Document] = self.retriever.invoke(question, filters=filters)
        return documents

    def retrieve(self, question: str):
        documents = self.get_documents(question)
        if len(documents) == 0:
            return "No supporting information found."

        # Generate content template
        content_template_str_lst = []
        for i in range(min(len(documents), 3)):
            content_template_str_lst += [
                f"<info{i+1}>",
                f"Source From: {{file{i+1}}}",
                f"{{context{i+1}}}",
                f"</info{i+1}>\n",
            ]
        content_template_str = "\n".join(content_template_str_lst)
        content_template = PromptTemplate.from_template(content_template_str)

        # Prepare contexts
        context_data = {}
        for i, doc in enumerate(documents[:3]):
            context_data[f"context{i+1}"] = doc.page_content
            context_data[f"file{i+1}"] = doc.metadata["file_name"]

        # Generate result
        result = content_template.invoke(context_data).text
        return result

    def single_rag(self, question: str) -> str:
        context = self.retrieve(question)
        return self.chain.invoke(
            {
                "system_prompt": DEFAULT_SYS_PROMPT_RAG,
                "context": context,
                "question": question,
            }
        )

    def simple_aoai(self, question: str = "Hello, I am Bob."):
        chain = self.llm | StrOutputParser()
        try:
            print(chain.invoke(question))
        except Exception as e:
            self.logger.error(f"Error invoking LLM: {e}")
