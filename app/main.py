import os
import sys
import uvicorn

from loguru import logger
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, Form
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, constr

from app.enums.action_enum import ActionEnum
from app.msg_format.response_model import ASSuccessResponseModel, ASErrorResponseModel, CSSuccessResponseModel, CSErrorResponseModel
from app.msg_format.request_model import ContractSearchRequestModel

load_dotenv('conf/.env')
app = FastAPI()

logger.remove()
logger.add(sys.stdout, level=os.getenv('LOG_LEVEL'))

# file type constraints
allowed_extensions = {".pdf", ".docx"}

@app.post("/", response_model=Union[ASSuccessResponseModel, ASErrorResponseModel])
async def auto_ai_service(
    action: ActionEnum = Form(...),
    question: Optional[constr(max_length=500)] = Form(None),
    text: Optional[str] = Form(None),
    conversationId: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    wordLimit: Optional[int] = Form(None, ge=1),
    file: UploadFile = File(...)
):

    logger.info(f"Received file: {file.filename} for action: {action}")
    # For actions other than 'summarize' or 'translate', ignore wordLimit if provided
    if action in [ActionEnum.summarize, ActionEnum.translate]:
        if wordLimit is None: wordLimit = 200
    else: wordLimit = None

    # Validate file type
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            message="Invalid file format. Only .pdf and .docx are supported.",
            errorCode=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Validate file size (max 10MB)
    try:
        file_size = len(await file.read())  # Read file to check size
        await file.seek(0)  # Reset pointer after reading
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail="Error processing the file")

    if file_size > 10 * 1024 * 1024:  # 10MB limit
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            message="File size exceeds the 10MB limit.",
            errorCode=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    question_is_empty = False
    if question is None or question is "": question_is_empty = True

    # Check if the action is 'qna' and enforce question as required
    if action == ActionEnum.qna and question_is_empty is True:
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            message="The 'question' parameter is required for 'qna' action.",
            errorCode=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Validate question length for 'qna' action
    if question and len(question) > 500:
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            message="The 'question' parameter cannot exceed 500 characters.",
            errorCode=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Check if 'text' is required for 'summarize' or 'translate'
    if action in [ActionEnum.summarize, ActionEnum.translate] and not text:
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            message="The 'text' parameter is required for 'summarize' or 'translate' action.",
            errorCode=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Simulated processing result
    if action == ActionEnum.summarize:
        result = "This contract outlines the payment terms, including deadlines and renewal conditions..."
    elif action == ActionEnum.translate:
        result = "我是翻譯機器人"
    else:
        result = "This is a smartest Q&A chatbot."

    return ASSuccessResponseModel(
        status="success",
        action=action.value,
        result=result,
        fileName=file.filename,
        language=language,
        wordLimit=wordLimit if wordLimit else None,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

@app.post("/contract_search", response_model=Union[CSSuccessResponseModel, CSErrorResponseModel])
async def contract_search(request: ContractSearchRequestModel):  # Use model here
    keyword = request.keyword
    # Simulated contract search logic
    # In a real-world application, this would involve querying a database or external service

    contracts = [
        {"contractId": "12345", "relevanceScore": 0.92},
        {"contractId": "67890", "relevanceScore": 0.88},
        {"contractId": "11223", "relevanceScore": 0.75},
    ]

    # Filter contracts based on the keyword (for simulation purposes, we assume all contracts match)
    matching_contracts = [contract for contract in contracts if contract["contractId"] == keyword]

    # If no matching contracts are found
    if not matching_contracts:
        return CSErrorResponseModel(
            status="error",
            message="No matching contracts found",
            errorCode=404,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Return success response with matching contracts
    return CSSuccessResponseModel(
        status="success",
        results=matching_contracts,
        keyword=keyword,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

@app.get("/health-check")
async def health_check():
    return {"status": "Alive"}

if __name__ == '__main__':
    uvicorn.run(
        app="main:app",
        host=os.getenv('APP_SERVER_HOST'),
        port=int(os.getenv('APP_SERVER_PORT')),
        workers=int(os.getenv('APP_SERVER_WORKER')),
    )