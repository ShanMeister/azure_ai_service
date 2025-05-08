from pydantic import BaseModel, constr, conint
from typing import Optional
from app.enums.action_enum import ActionEnum
from app.enums.system_enum import SystemEnum
from app.enums.search_enum import SearchTypeEnum
from fastapi import File, UploadFile

class AutoAIServiceRequestModel(BaseModel):
    action: ActionEnum  # This is already validated by FastAPI Enum
    question: Optional[constr(max_length=500)] = None  # Optional, max length 500 characters
    text: Optional[str] = None  # Optional text
    conversationId: Optional[str] = None  # Optional
    language: Optional[str] = None  # Optional
    wordLimit: Optional[int] = None  # Optional with validation (>=1)


class ContractSearchRequestModel(BaseModel):
    system_name: SystemEnum
    message_request: constr(max_length=5000)  # Max length constraint on keyword
    document_count: Optional[conint(ge=0)] = 5
    search_type: Optional[SearchTypeEnum] = "exact"