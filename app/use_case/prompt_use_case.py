import os
import re
from tiktoken import encoding_for_model
from app.utils.logger import init_logger
from app.repository.sys_prompt_services import SysPromptClass
from app.enums.prompt_enum import PromptEnum
from dotenv import load_dotenv

logger = init_logger()
load_dotenv('app/conf/.env')

class PromptUseCase:
    def __init__(self, prompt_service: SysPromptClass):
        self.prompt_service = prompt_service
        self.token_limit = int(os.getenv('TRANSLATE_CHUNK_SIZE'))
        self.encoding = encoding_for_model(os.getenv('AOAI_MODEL'))

    def _split_by_token(self, text: str, token_limit: int = 6000) -> list[str]:
        tokens = self.encoding.encode(text)
        chunks = [tokens[i:i + token_limit] for i in range(0, len(tokens), token_limit)]
        logger.info(f"Splitting context into {len(chunks)} chunks, each with up to {token_limit} tokens.")
        return [self.encoding.decode(chunk) for chunk in chunks]

    async def run_prompt(self, context: str, prompt_type: PromptEnum, response_language: str = None):
        if prompt_type == PromptEnum.translate:
            chunks = self._split_by_token(context, self.token_limit)
            results = []
            total = len(chunks)
            for i, chunk in enumerate(chunks, start=1):
                logger.info(f"Translating chunk {i} of {total}...")
                result = await self.prompt_service.set_prompt(chunk, prompt_type, response_language)
                cleaned = self.remove_figure_section(result)
                results.append(cleaned)
            logger.success(f"Translation completed. Total chunks processed: {total}.")
            return results[0]
        else:
            return await self.prompt_service.set_prompt(context, prompt_type, response_language)

    async def run_real_time_prompt(self, context: str, prompt_type: PromptEnum, message_request: str = None,
                                    response_language: str = None, chat_history: str = None):
        if prompt_type == PromptEnum.translate:
            chunks = self._split_by_token(context, self.token_limit)
            results = []
            total = len(chunks)
            for i, chunk in enumerate(chunks, start=1):
                logger.info(f"Translating chunk {i} of {total}...")
                result = await self.prompt_service.set_real_time_prompt(
                context=context,
                prompt_type=prompt_type,
                message_request=message_request,
                response_language=response_language,
                chat_history=chat_history
            )
                cleaned = self.remove_figure_section(result)
                results.append(cleaned)
            logger.success(f"Translation completed. Total chunks processed: {total}.")
            return results[0]
        else:
            return await self.prompt_service.set_real_time_prompt(
                context=context,
                prompt_type=prompt_type,
                message_request=message_request,
                response_language=response_language,
                chat_history=chat_history
            )

    def remove_figure_section(self, markdown_text: str):
        pattern = r"###\s*(Fig|Fig Source Info|圖片|圖源信息|圖片來源資訊)[\s\S]*?(?=(^#{1,6}\s)|\Z)"  # non-greedy 到下一個 heading 或結尾
        cleaned = re.sub(pattern, "", markdown_text, flags=re.MULTILINE)
        return cleaned