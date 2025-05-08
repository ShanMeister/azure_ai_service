from pydantic import BaseModel
from typing import Optional, List

# Success response model
class ASSuccessResponseModel(BaseModel):
    status: str = "success"
    action: str
    account_id: str
    document_id: str
    document_type: Optional[str] = None
    message_response: str
    file_name: str
    response_language: Optional[str] = None
    timestamp: str

# Error response model
class ASErrorResponseModel(BaseModel):
    status: str = "error"
    action: str
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
    chat_id: str
    sequence: Optional[str] = None
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

# Success response model for
class DRSuccessResponseModel(BaseModel):
    status: str = "success"
    document_id: str
    timestamp: str

# Error response model
class DRErrorResponseModel(BaseModel):
    status: str = "error"
    document_id: str
    error_message: str
    error_code: int
    timestamp: str