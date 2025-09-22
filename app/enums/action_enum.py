from enum import Enum

class ActionEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    qna = "qna"

class RealTimeActionEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    chat = "chat"