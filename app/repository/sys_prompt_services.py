import os
from app.utils.logger import init_logger
from typing import Optional
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
        self.env_name = os.getenv('ENV_NAME')

    async def set_prompt(self, context, prompt_type, response_language: Optional[str] = None):
        if prompt_type == PromptEnum.summarize:
            if self.env_name == "Nuvoton":
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or NTC or 新唐). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                    1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                    3. Do not include suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                    4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                    6. DO NOT write any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                    7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.
                    
                    LANGUAGE:
                    Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.
                    
                    CONTEXT:
                    ```markdown
                    {context}
                    ```
                    """
            else:
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or WEC or 華邦). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                    1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                    3. Do not include suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                    4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                    6. DO NOT write any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                    7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.

                    LANGUAGE:
                    Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.

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
            if self.env_name == "Nuvoton":
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or NTC or 新唐).
                    TASK:
                    Anticipate the key questions executives might ask before reviewing a contract. Generate exactly 5 insightful question-and-answer pairs tailored to executive concerns.  Follow these rules strictly:
                    - Each answer is clear and references relevant contract sections where applicable.
                    - Do not include suggestions, negotiation advice, or strategic tips. This FAQ is for informational purposes only.
                    - Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    - Ensure that every Q&A pair is written from {self.env_name}’s perspective, focusing on what is important or relevant to {self.env_name}.
                    - Base all questions and answers only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    - Cite the specific clause numbers wherever possible in the answers (e.g., “see Clause 5” or “see Section: Termination”). Use the original clause or heading as shown in the markdown.
                    - Use the term “payment terms” instead of “financial impact” when referring to related clauses.
                    - The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate and reference source sections.
                    LANGUAGE:
                    - Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.
                    OUTPUT FORMAT:
                    - Provide only the numbered list of 5 Q&A items.
                    - Each pair must use the following format:
                        [Qusetion number]. 
                            Q: [Question text]
                            A: [Answer text]
                    - Do NOT include any introductions, explanations, or summary statements before or after the Q&A list.
                    - Begin directly with "1." and continue through "5."
                    - Keep the Q&A concise, clear, and professional.
                    CONTEXT:
                    ```markdown
                    {context}
                    ```
                    """
            else:
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or WEC or 華邦).
                    TASK:
                    Anticipate the key questions executives might ask before reviewing a contract. Generate exactly 5 insightful question-and-answer pairs tailored to executive concerns.  Follow these rules strictly:
                    - Each answer is clear and references relevant contract sections where applicable.
                    - Do not include suggestions, negotiation advice, or strategic tips. This FAQ is for informational purposes only.
                    - Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    - Ensure that every Q&A pair is written from {self.env_name}’s perspective, focusing on what is important or relevant to {self.env_name}.
                    - Base all questions and answers only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    - Cite the specific clause numbers wherever possible in the answers (e.g., “see Clause 5” or “see Section: Termination”). Use the original clause or heading as shown in the markdown.
                    - Use the term “payment terms” instead of “financial impact” when referring to related clauses.
                    - The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate and reference source sections.
                    LANGUAGE:
                    - Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.
                    OUTPUT FORMAT:
                    - Provide only the numbered list of 5 Q&A items.
                    - Each pair must use the following format:
                        [Qusetion number]. 
                            Q: [Question text]
                            A: [Answer text]
                    - Do NOT include any introductions, explanations, or summary statements before or after the Q&A list.
                    - Begin directly with "1." and continue through "5."
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
            if self.env_name == "Nuvoton":
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or NTC or 新唐). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                    1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                    3. Do not include suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                    4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                    6. DO NOT write any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                    7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.
                    
                    LANGUAGE:
                    Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.
                    
                    CONTEXT:
                    ```markdown
                    {context}
                    ```
                    """
            else:
                prompt_text = f"""
                    You are a lawyer representing {self.env_name} (or WEC or 華邦). Summarize this contract from {self.env_name}'s perspective in a clear, concise, and executive-friendly manner. Follow these rules strictly:
                    1. Base your summary only on what is explicitly written in the contract. Avoid adding, omitting, or altering any information. Do not infer, predict, or extend beyond the provided content.
                    2. Cite the specific clause numbers wherever possible (e.g., “see Clause 5”) to support your summary.
                    3. Do not include suggestions, negotiation advice, or strategic tips. This summary is for informational purposes only.
                    4. Avoid character confusion. Always present {self.env_name}'s responsibilities, rights, and obligations clearly from {self.env_name}'s point of view.
                    5. Use the term “payment terms” instead of “financial impact” when summarizing related clauses.
                    6. DO NOT write any introduction, explanation, or additional description before or after the output. Only return the clean summary content.
                    7. The contract is provided in Markdown format. Use the Markdown headings and numbered clauses to locate.

                    LANGUAGE:
                    Your response MUST be written in {response_language}. Do not use any other language or deviate from the specified format. If the desired response language is traditional chinese, you MUST always write in Traditional Chinese — even if the contract is written in Simplified Chinese.

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
        return response
