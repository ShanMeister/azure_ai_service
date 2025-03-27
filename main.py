import os
import sys
import uvicorn
import asyncio
from loguru import logger
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, Form
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, constr

from app.enums.action_enum import ActionEnum
from app.enums.prompt_enum import PromptEnum
from app.msg_format.response_model import ASSuccessResponseModel, ASErrorResponseModel, CSSuccessResponseModel, CSErrorResponseModel
from app.msg_format.request_model import ContractSearchRequestModel
from app.use_case.pdf_processing import PDFProcessingUseCase
from src.doc2rag.pipeline.file_flows import file_initialize_flow
from app.utils.file_process import FileProcessClass
from app.use_case.sys_prompt import SysPromptClass
from pipeline import run_ai_service_pipeline
from app.use_case.rag_processing import RAGUseCase
# from contextlib import asynccontextmanager
# from apscheduler.schedulers.asyncio import AsyncIOScheduler

# scheduler = AsyncIOScheduler()
load_dotenv('conf/.env')
app = FastAPI()
logger.remove()
logger.add(sys.stdout, level=os.getenv('LOG_LEVEL'))

pdf_use_case_object = PDFProcessingUseCase()
rag_use_case_object = RAGUseCase()
file_process_object = FileProcessClass()
sys_prompt_object = SysPromptClass()

file_initialize_flow()

# file type constraints
allowed_extensions = {".pdf", ".docx"}

@app.post("/ai_service", response_model=Union[ASSuccessResponseModel, ASErrorResponseModel])
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
    pdf_bytes = await file.read()
    try:
        file_size = len(pdf_bytes)  # Read file to check size
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
    if question is None or question == "": question_is_empty = True

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

    logger.info(f"Received file: {file.filename} for action: {action}")
    # Simulated processing result
    if action == ActionEnum.summarize:
        save_file_path = r"C:\projects\NuECS\test_cases\test_07\source\csmtest20250320\text_image\wait"
        os.makedirs(save_file_path, exist_ok=True)
        save_path = os.path.join(save_file_path, file.filename)
        await file_process_object.save_upload_file(file, save_path)
        merged_bundle = await run_ai_service_pipeline()
        if merged_bundle is None and merged_bundle == "":
            result = None
            logger.error(f" Fail to get summarize result from AOAI: {result}")
            # raise HTTPException(status_code=500, detail="Error processing the markdown file, return empty file.")
        else:
            result = sys_prompt_object.set_prompt(merged_bundle, PromptEnum.summarize, question)
            print(result)
            logger.info(f" Success to get summarize result from AOAI: {result}")
    elif action == ActionEnum.translate:
        save_file_path = r"C:\projects\NuECS\test_cases\test_07\source\csmtest20250320\text_image\wait"
        os.makedirs(save_file_path, exist_ok=True)
        save_path = os.path.join(save_file_path, file.filename)
        await file_process_object.save_upload_file(file, save_path)
        merged_bundle = await run_ai_service_pipeline()
        if merged_bundle is None and merged_bundle == "":
            result = None
            logger.error(f" Fail to get translate result from AOAI: {result}")
            # raise HTTPException(status_code=500, detail="Error processing the markdown file, return empty file.")
        else:
            result = sys_prompt_object.set_prompt(merged_bundle, PromptEnum.translate, question)
            print(result)
            logger.info(f" Success to get translate result from AOAI: {result}")
    else:
        save_file_path = r"C:\projects\NuECS\test_cases\test_07\source\csmtest20250320\text_image\wait"
        os.makedirs(save_file_path, exist_ok=True)
        save_path = os.path.join(save_file_path, file.filename)
        await file_process_object.save_upload_file(file, save_path)
        merged_bundle = await run_ai_service_pipeline()
        if merged_bundle is None and merged_bundle == "":
            result = None
            logger.error(f" Fail to get qna result from AOAI: {result}")
            # raise HTTPException(status_code=500, detail="Error processing the markdown file, return empty file.")
        else:
            result = sys_prompt_object.set_prompt(merged_bundle, PromptEnum.qna, question)
            logger.info(f" Success to get qna result from AOAI: {result}")

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

    matching_contracts = rag_use_case_object.run_rag_flow(keyword, 1)

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


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger.info("Application startup: initializing scheduler...")
#     await asyncio.sleep(1)
#     schedule_pipeline()
#     yield
#     logger.info("Application shutdown: shutting down scheduler...")
#     scheduler.shutdown(wait=False)
#
# app.router.lifespan_context = lifespan

if __name__ == '__main__':
    uvicorn.run(
        app="main:app",
        host=os.getenv('APP_SERVER_HOST'),
        port=int(os.getenv('APP_SERVER_PORT')),
        workers=int(os.getenv('APP_SERVER_WORKER')),
    )