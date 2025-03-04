from pydantic import BaseModel
from typing import Optional, List

# Success response model
class ASSuccessResponseModel(BaseModel):
    status: str = "success"
    action: str
    result: str
    fileName: str
    language: Optional[str] = None
    wordLimit: Optional[int] = None
    timestamp: str

# Error response model
class ASErrorResponseModel(BaseModel):
    status: str = "error"
    action: str
    message: str
    errorCode: int
    timestamp: str

# Success response model for contract search
class CSSuccessResponseModel(BaseModel):
    status: str = "success"
    results: List[dict]  # List of dictionaries with contractId and relevanceScore
    keyword: str
    timestamp: str

# Error response model for contract search
class CSErrorResponseModel(BaseModel):
    status: str = "error"
    message: str
    errorCode: int
    timestamp: str