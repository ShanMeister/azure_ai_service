# app/schemas.py
from pydantic import BaseModel
from typing import Optional

class DocumentRecordCreate(BaseModel):
    doc_id: str
    ai_search_id: str
    file_name: str
    doc_content: Optional[str] = None
    preprocessed_content: Optional[str] = None
    translated_context: Optional[str] = None
    summarized_context: Optional[str] = None
    qna_context: Optional[str] = None
    created_by: str
    updated_by: str

    class Config:
        orm_mode = True

class DocumentRecordUpdate(BaseModel):
    file_name: str
    doc_content: Optional[str] = None
    preprocessed_content: Optional[str] = None
    translated_context: Optional[str] = None
    summarized_context: Optional[str] = None
    qna_context: Optional[str] = None
    updated_by: str

    class Config:
        orm_mode = True
