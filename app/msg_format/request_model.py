from pydantic import BaseModel, constr
from typing import Optional
from app.enums.action_enum import ActionEnum
from fastapi import File, UploadFile

class AutoAIServiceRequestModel(BaseModel):
    action: ActionEnum  # This is already validated by FastAPI Enum
    question: Optional[constr(max_length=500)] = None  # Optional, max length 500 characters
    text: Optional[str] = None  # Optional text
    conversationId: Optional[str] = None  # Optional
    language: Optional[str] = None  # Optional
    wordLimit: Optional[int] = None  # Optional with validation (>=1)


class ContractSearchRequestModel(BaseModel):
    keyword: constr(max_length=100)  # Max length constraint on keyword