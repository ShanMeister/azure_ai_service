import os
from loguru import logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from src.doc2rag.config_utils import PathConfig

load_dotenv('conf/.env')

class SysPromptClass:
    def __init__(self):
        self.path_config = PathConfig()
        self.template = """
            Context:
            {context}

            Query:
            {query}
            """

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "This is the file content: {context}"),
                ("human", "This is my question: {query}"),
            ]
        )

        self.model = init_chat_model(
            model_provider=os.getenv('AOAI_MODEL_PROVIDER'),
            model=os.getenv('AOAI_MODEL'),
            azure_deployment=os.getenv('AOAI_DEPLOYMENT'),
            azure_endpoint=os.getenv('AOAI_ENDPOINT'),
            api_key=os.getenv('AOAI_API_KEY'),
            api_version=os.getenv('AOAI_API_VERSION'),
        )
        pass


    def set_prompt(self, context, prompt_type, question):
        if prompt_type == "summarize":
            prompt_text = f"""
                You are a legal expert specializing in contract analysis.

                TASK:
                Summarize this contract in a clear, concise, and executive-friendly manner, focusing on key terms, obligations, risks, financial implications, compliance requirements, termination clauses, and negotiation points. Ensure accuracy while eliminating unnecessary legal jargon. Highlight any unusual or high-risk clauses and reference relevant sections where applicable.

                CONTEXT:
                ```markdown
                {context}
                ```

                OUTPUT FORMAT:
                - Provide a clear, concise summary.
                - Focus on key terms, obligations, risks, financial implications, compliance requirements, termination clauses, and negotiation points.
                - Ensure accuracy while eliminating unnecessary legal jargon.
                - Highlight any unusual or high-risk clauses and reference relevant sections where applicable.
                """
        elif prompt_type == "translate":
            prompt_text = f"""
                You are a legal expert specializing in contract translation.

                TASK:
                You always provide fact-based information, and would never make anything up. Translate the following text, if the test is in english, translate it into traditional chinese, otherwise, translate it into english.

                CONTEXT:
                ```markdown
                {context}
                ```

                OUTPUT FORMAT:
                - Provide a precise and professional translation.
                - Ensure factual accuracy and preserve the original legal meaning.
                - Avoid adding or omitting information.
                - Format the translation as close to the original as possible.
                """
        elif prompt_type == "qna":
            prompt_text = f"""
                You are a legal expert specializing in contract analysis for executives.

                TASK:
                 Your task is to anticipate key questions executives might ask before reviewing a contract. Generate 10 insightful Q&A tailored to their needs, covering critical areas such as risks, liabilities, obligations, financial impact, compliance, termination clauses, and negotiation leverage. Ensure the questions are strategic, concise, and actionable, with clear and precise answers that reference relevant contract sections where applicable.

                CONTEXT:
                ```markdown
                {context}
                ```
                """
        else:
            raise ValueError(f"Unsupported prompt type: {prompt_type}")

        chain = self.model | StrOutputParser()
        response = chain.invoke(prompt_text)
        logger.info(f"Success get response from AOAI: {response}")
        return response
