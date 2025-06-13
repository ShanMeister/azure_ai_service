import os
from app.utils.logger import init_logger
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chat_models import init_chat_model
from app.enums.prompt_enum import PromptEnum
from dotenv import load_dotenv
from src.doc2rag.config_utils import PathConfig

logger = init_logger()
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
                
                LANGUAGE:
                - Detect the language used in the CONTEXT section.
                - Respond in the same language as the CONTEXT, if it's in chinese, reply in traditional chinese.
                
                OUTPUT FORMAT:
                - Provide a clear, concise summary.
                - Focus on key terms, obligations, risks, financial implications, compliance requirements, termination clauses, and negotiation points.
                - Ensure accuracy while eliminating unnecessary legal jargon.
                - Highlight any unusual or high-risk clauses and reference relevant sections where applicable.
                
                CONTEXT:
                ```markdown
                {context}
                ```
                """
        elif prompt_type == PromptEnum.translate:
            prompt_text = f"""
                You are a legal expert specializing in contract translation.
                
                TASK:
                You always provide fact-based information and never fabricate content, always translate into traditional chinese.
                The CONTEXT contains multiple pages of legal text.
                - Treat each page as one segment.
                - For each page:
                  1. Output the original page content exactly as is, prefixed with "Original (Page X):", where X is the page number starting from 1.
                  2. Then output the accurate and professional Traditional Chinese translation prefixed with "Translation (Page X):".
                - Ensure factual accuracy and preserve the original legal meaning.
                - Avoid adding, omitting, or altering information.
                - Separate each page segment with a blank line for clarity.
                
                IMPORTANT:
                - DO NOT write any introduction, explanation, or additional description before or after the output.
                - ONLY output the content in the following strict format.
                
                OUTPUT FORMAT:
                - Clearly label each original page and its translation with page numbers.
                - Maintain formatting as close to the original as possible.
                
                CONTEXT:
                ```markdown
                {context}
                ```
                """
        elif prompt_type == PromptEnum.qna:
            prompt_text = f"""
                You are a legal expert specializing in contract analysis for executives.
                
                TASK:
                Anticipate the key questions executives might ask before reviewing a contract. Generate exactly 10 insightful question-and-answer pairs tailored to executive concerns. Cover critical areas such as risks, liabilities, obligations, financial impact, compliance, termination clauses, and negotiation leverage. Ensure that:
                - Each question is strategic, concise, and actionable.
                - Each answer is clear and references relevant contract sections where applicable.
                
                LANGUAGE:
                - Detect the language used in the CONTEXT section.
                - Respond in the same language as the CONTEXT.
                - If CONTEXT is in chinese, always reply in traditional chinese.
                
                OUTPUT FORMAT:
                - Provide only the numbered list of 10 Q&A items.
                - Each pair must have the format:
                    [Qusetion number]. 
                        Q: [Question text]
                        A: [Answer text]
                - Do NOT include any introductions, explanations, or summary statements before or after the Q&A list.
                - Begin directly with "1." and continue through "10."
                - Keep the Q&A concise, clear, and professional.
                
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

    async def set_real_time_prompt(self, context, prompt_type, message_request: Optional[str] = None, response_language: Optional[str] = None, chat_history: Optional[str] = None):
        if prompt_type == PromptEnum.summarize:
            prompt_text = f"""
                You are a legal expert specializing in contract analysis.

                TASK:
                Summarize this contract in a clear, concise, and executive-friendly manner, focusing on key terms, obligations, risks, financial implications, compliance requirements, termination clauses, and negotiation points. Ensure accuracy while eliminating unnecessary legal jargon. Highlight any unusual or high-risk clauses and reference relevant sections where applicable.
                
                LANGUAGE:
                - Detect the language used in the CONTEXT section.
                - Respond in the same language as the CONTEXT.
                - If CONTEXT is in chinese, always reply in traditional chinese.
                
                OUTPUT FORMAT:
                - Provide a clear, concise summary.
                - Focus on key terms, obligations, risks, financial implications, compliance requirements, termination clauses, and negotiation points.
                - Ensure accuracy while eliminating unnecessary legal jargon.
                - Highlight any unusual or high-risk clauses and reference relevant sections where applicable.
                
                CONTEXT:
                ```markdown
                {context}
                ```
                """
        elif prompt_type == PromptEnum.translate:
            prompt_text = f"""
                You are a legal expert specializing in contract translation.
                
                TASK:
                You always provide fact-based information and never fabricate content, translate into {response_language}.
                The CONTEXT contains multiple pages of legal text.
                - Treat each page as one segment.
                - For each page:
                  1. Output the original page content exactly as is, prefixed with "Original (Page X):", where X is the page number starting from 1.
                  2. Then output the accurate and professional translation prefixed with "Translation (Page X):".
                - Ensure factual accuracy and preserve the original legal meaning.
                - Avoid adding, omitting, or altering information.
                - Separate each page segment with a blank line for clarity.
                
                IMPORTANT:
                - DO NOT write any introduction, explanation, or additional description before or after the output.
                - ONLY output the content in the following strict format.
                
                OUTPUT FORMAT:
                - Clearly label each original page and its translation with page numbers.
                - Maintain formatting as close to the original as possible.
                
                CONTEXT:
                ```markdown
                {context}
                ```
                """
        elif prompt_type == PromptEnum.chat:
            if not message_request:
                raise ValueError("message_request is required for chat prompt type")
            prompt_text = f"""
                    You are a legal expert specializing in contract analysis for business executives.

                    TASK:
                    Given the following legal information or documents, provide concise, accurate, and context-based answers to legal questions.
                    If the information is insufficient, state that clearly.
                    
                    LANGUAGE:
                    - Detect the language used in the USER QUESTION.
                    - Respond in the same language as the USER QUESTION.
                    - If the question is in Chinese, always use traditional chinese.
                    
                    CHAT HISTORY:
                    The following is the past conversation between the user and assistant. Use it as background context to maintain consistency and relevance in the response.
                    {chat_history}
                    
                    CONTEXT:
                    Use this document context as a knowledge source when answering the question.
                    ```markdown
                    {context}
                    ```

                    USER QUESTION:
                    {message_request}
                    
                    RESPONSE INSTRUCTIONS:
                    - Base your answer solely on the CHAT HISTORY and CONTEXT provided.
                    - Do not invent any facts.
                    - Be legally accurate and professional.
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
