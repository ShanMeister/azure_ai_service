from pydantic import BaseModel
from typing import Optional, List

class AIServiceResultModel(BaseModel):
    summarize: str
    translate: str
    qna: str
    processed_content: str

class ExpiredContractResultModel(BaseModel):
    processed_content: str

# Success response model
class ASSuccessResponseModel(BaseModel):
    status: str = "success"
    action: Optional[str] = None
    account_id: str
    document_id: str
    document_type: Optional[str] = None
    message_response: AIServiceResultModel
    file_name: str
    response_language: Optional[str] = None
    timestamp: str

# Error response model
class ASErrorResponseModel(BaseModel):
    status: str = "error"
    action: Optional[str] = None
    error_message: str
    error_code: int
    timestamp: str

# Success response model for contract search
class CSSuccessResponseModel(BaseModel):
    status: str = "success"
    results: List[dict] = []  # List of dictionaries with contractId and relevanceScore
    request : str
    timestamp: str

# Error response model for contract search
class CSErrorResponseModel(BaseModel):
    status: str = "error"
    error_message: str
    error_code: int
    timestamp: str

# Success response model for real-time ai service
class RTASSuccessResponseModel(BaseModel):
    status: str = "success"
    action: str
    account_id: str
    chat_id: Optional[str] = None
    message_request: Optional[str] = None
    message_response: str
    file_name: str
    timestamp: str

# Error response model for real-time ai service
class RTASErrorResponseModel(BaseModel):
    status: str = "error"
    action: str
    error_message: str
    error_code: int
    timestamp: str

# Success response model for delete record
class DRSuccessResponseModel(BaseModel):
    status: str = "success"
    document_id: str
    file_name: str
    timestamp: str

# Error response model for delete record
class DRErrorResponseModel(BaseModel):
    status: str = "error"
    document_id: str
    file_name: str
    error_message: str
    error_code: int
    timestamp: str

# Success response model for expired contract preprocess
class EXCPSuccessResponseModel(BaseModel):
    status: str = "success"
    account_id: str
    document_id: str
    message_response: ExpiredContractResultModel
    file_name: str
    timestamp: str

# Error response model for expired contract preprocess
class EXCPErrorResponseModel(BaseModel):
    status: str = "error"
    error_message: str
    error_code: int
    timestamp: str