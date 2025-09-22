from enum import Enum

class PromptEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    qna = "qna"
    chat = "chat"
    search = "search"