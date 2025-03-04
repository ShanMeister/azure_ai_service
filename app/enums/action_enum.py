from enum import Enum

class ActionEnum(str, Enum):
    summarize = "summarize"
    translate = "translate"
    qna = "qna"