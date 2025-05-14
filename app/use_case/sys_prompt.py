import os
from loguru import logger
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from app.enums.prompt_enum import PromptEnum
from dotenv import load_dotenv
from src.doc2rag.config_utils import PathConfig

load_dotenv('app/conf/.env')

class SysPromptClass:
    def __init__(self):
        self.path_config = PathConfig()
        self.model = init_chat_model(
            model_provider=os.getenv('AOAI_MODEL_PROVIDER'),
            model=os.getenv('AOAI_MODEL'),
            azure_deployment=os.getenv('AOAI_DEPLOYMENT'),
            azure_endpoint=os.getenv('AOAI_ENDPOINT'),
            api_key=os.getenv('AOAI_API_KEY'),
            api_version=os.getenv('AOAI_API_VERSION'),
        )

    async def set_prompt(self, context, prompt_type):
        if prompt_type == PromptEnum.summarize:
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
        elif prompt_type == PromptEnum.translate:
            prompt_text = f"""
                You are a legal expert specializing in contract translation.

                TASK:
                You always provide fact-based information, and would never make anything up. Translate the following text, translate it into traditional chinese, except the text are already in traditional chinese.

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
        elif prompt_type == PromptEnum.qna:
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
        try:
            response = await chain.ainvoke(prompt_text)
        except Exception as e:
            logger.error(f"Prompt execution failed: {str(e)}")
            raise
        logger.info(f"Success get {prompt_type} response from AOAI...")
        return response

    async def set_real_time_prompt(self, context, prompt_type, message_request: Optional[str] = None, response_language: Optional[str] = None):
        if prompt_type == PromptEnum.summarize:
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
        elif prompt_type == PromptEnum.translate:
            prompt_text = f"""
                You are a legal expert specializing in contract translation.

                TASK:
                You always provide fact-based information, and would never make anything up. Translate the following text into {response_language}.

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
        elif prompt_type == PromptEnum.chat:
            if not message_request:
                raise ValueError("message_request is required for chat prompt type")
            prompt_text = f"""
                    You are a legal expert specializing in contract analysis for business executives.

                    TASK:
                    Given the following legal information or documents, provide concise, accurate, and context-based answers to legal questions.
                    If the information is insufficient, state that clearly.

                    CONTEXT:
                    ```markdown
                    {context}
                    ```

                    USER QUESTION:
                    {message_request}
                    """
        else:
            raise ValueError(f"Unsupported prompt type: {prompt_type}")

        chain = self.model | StrOutputParser()
        try:
            response = await chain.ainvoke(prompt_text)
        except Exception as e:
            logger.error(f"Prompt execution failed: {str(e)}")
            raise
        logger.info(f"Success get {prompt_type} response from AOAI...")
        return {
            "prompt_type": prompt_type,
            "response": response,
            "success": True
        }
