from app.repository.repository import ChatRecordRepository
from app.enums.chat_role_enum import RoleEnum
from app.enums.schema_enum import ChatRecordCreate
from typing import List

class ChatUseCase:
    def __init__(self):
        pass

    # def build_context_from_history(
    #     self,
    #     chat_id: str,
    #     sequence: int,
    #     doc_context: str,
    #     message_request: str,
    #     window: int = 5
    # ) -> str:
    #     """
    #     整合過去最多 `window` 則的對話，加上 doc_context，產出最終 context 字串
    #     """
    #     # 1. 抓取過去的對話紀錄（依 sequence 排序，僅取在當前 sequence 之前的）
    #     histories = self.repo.get_history_by_chat_id(chat_id)
    #     histories = [h for h in histories if h.sequence < sequence]
    #     histories = sorted(histories, key=lambda x: x.sequence)[-window:]  # 最多取 window 則
    #
    #     # 2. 將紀錄格式化為 "Q: ...\nA: ..." 形式
    #     conversation_context = ""
    #     for record in histories:
    #         prefix = "Q: " if record.role == RoleEnum.user else "A: "
    #         conversation_context += f"{prefix}{record.message}\n"
    #
    #     # 3. 加上當前的文件內容與 user 問句
    #     final_context = f"This is the conversation history between you and user：\n{conversation_context}\n"
    #     return final_context

    def build_context_from_history(
            self,
            histories: list,
            sequence: int,
            window: int = 20
    ) -> str:
        """
        整合過去最多 `window` 則的對話，加上 doc_context，產出最終 context 字串
        """
        # 過濾並排序
        filtered = [h for h in histories if h.sequence < sequence]
        filtered = sorted(filtered, key=lambda x: x.sequence)[-window:]

        # 格式化為 Q/A 對話
        conversation_context = ""
        for record in filtered:
            prefix = "Q: " if record.role == RoleEnum.user else "A: "
            conversation_context += f"{prefix}{record.message}\n"

        # 加上 context 與使用者問題
        final_context = f"This is the conversation history between you and user：\n{conversation_context}"
        return final_context