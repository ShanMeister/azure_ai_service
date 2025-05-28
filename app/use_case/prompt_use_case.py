import re
from app.repository.sys_prompt_services import SysPromptClass
from app.enums.prompt_enum import PromptEnum

class PromptUseCase:
    def __init__(self, prompt_service: SysPromptClass):
        self.prompt_service = prompt_service

    async def run_prompt(self, context: str, prompt_type: PromptEnum):
        return await self.prompt_service.set_prompt(context, prompt_type)

    async def run_real_time_prompt(self, context: str, prompt_type: PromptEnum, message_request: str = None,
                                    response_language: str = None, chat_history: str = None):
        result_context = await self.prompt_service.set_real_time_prompt(
            context=context,
            prompt_type=prompt_type,
            message_request=message_request,
            response_language=response_language,
            chat_history=chat_history
        )
        if prompt_type == PromptEnum.translate:
            processed_context = self.remove_figure_section(result_context['response'])
            result_context['response'] = processed_context
        return result_context

    def remove_figure_section(self, markdown_text: str):
        pattern = r"###\s*(Fig|Fig Source Info|圖片|圖源信息|圖片來源資訊)[\s\S]*?(?=(^#{1,6}\s)|\Z)"  # non-greedy 到下一個 heading 或結尾
        cleaned = re.sub(pattern, "", markdown_text, flags=re.MULTILINE)
        return cleaned
