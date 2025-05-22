import os
import sys
import uvicorn
import uuid

from exceptiongroup import catch
from app.utils.logger import init_logger
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.enums.system_enum import SystemEnum
from app.enums.action_enum import ActionEnum, RealTimeActionEnum
from app.enums.prompt_enum import PromptEnum
from app.enums.search_enum import SearchTypeEnum, SearchThresholdEnum
from app.enums.translation_enum import TranslationEnum
from app.enums.schema_enum import DocumentRecordCreate, DocumentRecordUpdate, ChatRecordCreate, ChatRecordUpdate
from app.enums.chat_role_enum import RoleEnum
from app.msg_format.response_model import ASSuccessResponseModel, ASErrorResponseModel, CSSuccessResponseModel, CSErrorResponseModel, RTASSuccessResponseModel, RTASErrorResponseModel, DRSuccessResponseModel, DRErrorResponseModel, AIServiceResultModel, EXCPSuccessResponseModel, EXCPErrorResponseModel, ExpiredContractResultModel
from src.doc2rag.pipeline.file_flows import file_initialize_flow
from app.utils.file_process import FileProcessClass
from app.use_case.sys_prompt import SysPromptClass
from pipeline import run_ai_service_pipeline
from app.use_case.rag_processing import RAGUseCase
from app.repository.database import Database, get_db
from app.repository.repository import DocumentRepository, ChatRecordRepository
from app.use_case.ai_search_use_case import AISearchUseCase
from app.use_case.file_processing import FileProcessUseCase
from app.use_case.chat_use_case import ChatUseCase

load_dotenv('app/conf/.env')
logger = init_logger()
logger.info("Application starting...")

# file type constraints
allowed_extensions = {".pdf", ".docx"}
SAVE_FILE_PATH = os.getenv('SAVE_API_FILE_PATH')

# === Lifespan Event ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.db = Database().connect()
        logger.info("Successfully connected to the database.")
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        raise RuntimeError("Database connection failed.") from e

    file_initialize_flow()

    yield

    # 關閉資料庫連線
    if hasattr(app.state, "db"):
        app.state.db._engine.dispose()
        logger.info("Database connection closed.")


# === FastAPI App ===
app = FastAPI(lifespan=lifespan)

# pdf_use_case_object = PDFProcessingUseCase()
rag_use_case_object = RAGUseCase()
file_process_object = FileProcessClass()
sys_prompt_object = SysPromptClass()
fast_file_process_object = FileProcessUseCase()
ai_search_use_case_object = AISearchUseCase()
chat_use_case_object = ChatUseCase()


# API-1 service
@app.post("/ai_service", responses={
    200: {"model": ASSuccessResponseModel},
    400: {"model": ASErrorResponseModel},
    500: {"model": ASErrorResponseModel}
})
async def auto_ai_service(
    system_name: SystemEnum = Form(...),
    action: Optional[ActionEnum] = Form(None),
    account_id: str = Form(...),
    document_id: str = Form(...),
    document_type: Optional[str] = Form(None),
    response_language: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    output_format: Optional[str] = Form(None),
    file: UploadFile = File(...)
):

    logger.info(f"Received file: {file.filename}")

    # Validate file type
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        return ASErrorResponseModel(
            status="error",
            action=action.value,
            error_message="Invalid file format. Only .pdf and .docx are supported.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    try:
        # Validate file size (max 10MB)
        pdf_bytes = await file.read()
        file_size = len(pdf_bytes)  # Read file to check size
        await file.seek(0)  # Reset pointer after reading
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail="Error processing the file")

    if file_size > 10 * 1024 * 1024:  # 10MB limit
        return ASErrorResponseModel(
            status="error",
            action=None,
            error_message="File size exceeds the 10MB limit.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Check if 'text' is required for 'summarize' or 'translate'
    if not account_id:
        return ASErrorResponseModel(
            status="error",
            action=None,
            error_message="The 'account_id' parameter is required.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    current_step=''
    try:
        merged_bundle = await handle_action(file)
        current_step = "summarize"
        summarized_result = await sys_prompt_object.set_prompt(merged_bundle, PromptEnum.summarize)
        logger.info(f"Success to get result from AOAI for {PromptEnum.summarize}: {summarized_result}")

        current_step = "translate"
        translated_result = await sys_prompt_object.set_prompt(merged_bundle, PromptEnum.translate)
        logger.info(f"Success to get result from AOAI for {PromptEnum.translate}: {translated_result}")

        current_step = "qna"
        qna_result = await sys_prompt_object.set_prompt(merged_bundle, PromptEnum.qna)
        logger.info(f"Success to get result from AOAI for {PromptEnum.qna}: {qna_result}")
        preprocessed_data = merged_bundle

    except Exception as e:
        logger.error(f"LLM service failed during {current_step}: {e}")
        return ASErrorResponseModel(
            status="error",
            action=current_step,
            error_message=f"Error while processing '{current_step}' service.",
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    if not any([summarized_result, translated_result, qna_result]):
        return ASErrorResponseModel(
            status="error",
            action=None,
            error_message="Empty response from AOAI service. Please try again later.",
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Insert contract record into DB
    try:
        with app.state.db.get_session() as session:
            doc_repo = DocumentRepository(session)
            existing_doc = await doc_repo.get_document_by_id_and_file_name(document_id, file.filename)

            if existing_doc:
                old_ai_search_id = existing_doc.ai_search_id
                update_data = DocumentRecordUpdate(
                    file_name=file.filename,
                    preprocessed_content=preprocessed_data,
                    translated_context=translated_result,
                    summarized_context=summarized_result,
                    qna_context=qna_result,
                    updated_by=account_id
                )
                await doc_repo.update_document(document_id, update_data)

                await ai_search_use_case_object.delete_document(old_ai_search_id)
                await ai_search_use_case_object.upload_single_document(
                    id=old_ai_search_id,
                    file_id=document_id,
                    file_name=file.filename,
                    content=preprocessed_data
                )
            else:
                ai_search_id = str(uuid.uuid4())
                create_data = DocumentRecordCreate(
                    doc_id=document_id,
                    file_name=file.filename,
                    ai_search_id=ai_search_id,
                    doc_content=None,
                    preprocessed_content=preprocessed_data,
                    translated_context=translated_result,
                    summarized_context=summarized_result,
                    qna_context=qna_result,
                    created_by=account_id,
                    updated_by=account_id
                )
                await doc_repo.create_document(create_data)

                await ai_search_use_case_object.upload_single_document(
                    id=ai_search_id,
                    file_id=document_id,
                    file_name=file.filename,
                    content=preprocessed_data
                )

    except Exception as e:
        logger.error(f"DB insert error: {e}")
        return ASErrorResponseModel(
            status="error",
            action=None,
            error_message="Internal server error when saving result to DB.",
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    return ASSuccessResponseModel(
        status="success",
        action=None,
        account_id=account_id,
        document_id=document_id,
        document_type=document_type if document_type else None,
        message_response=AIServiceResultModel(
            summarize=summarized_result,
            translate=translated_result,
            qna=qna_result,
            processed_content=preprocessed_data
        ),
        file_name=file.filename,
        response_language=response_language,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

# API-2 service
@app.post("/contract_search", responses={
    200: {"model": CSSuccessResponseModel},
    400: {"model": CSErrorResponseModel},
    500: {"model": CSErrorResponseModel}
})
async def contract_search(
    system_name: SystemEnum = Form(...),
    message_request: str = Form(...),
    document_count: int = Form(ge=1, le=10000),
    search_type: Optional[SearchTypeEnum] = Form(None)
    ):  # Use model here
    message = message_request
    count = document_count or 10
    # if search_type == SearchTypeEnum.fuzzy_matching:
    #     threshold = SearchThresholdEnum.fuzzy
    # elif search_type == SearchTypeEnum.exact_matching:
    #     threshold = SearchThresholdEnum.exact
    # else:
    #     return CSErrorResponseModel(
    #         status="error",
    #         message="Not allowed search type.Please try again later.",
    #         errorCode=400,
    #         timestamp=datetime.utcnow().isoformat() + "Z"
    #     )
    logger.info(f"Searching file with similarity threshold: {SearchThresholdEnum.fuzzy}")
    threshold = float(SearchThresholdEnum.fuzzy)

    matching_contracts = rag_use_case_object.run_rag_flow(message, count, threshold)

    # If no matching contracts are found
    if not matching_contracts:
        matching_contracts = []

    # Return success response with matching contracts
    return CSSuccessResponseModel(
        status="success",
        results=matching_contracts,
        request=message,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

# API-3 service
@app.post("/real_time_ai_service", responses={
    200: {"model": RTASSuccessResponseModel},
    400: {"model": RTASErrorResponseModel},
    500: {"model": RTASErrorResponseModel}
})
async def real_time_ai_service(
    system_name: SystemEnum= Form(...),
    action: RealTimeActionEnum = Form(...),
    account_id: Optional[str] = Form(...),
    document_id: Optional[str] = Form(None),
    processed_content: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    chat_id : Optional[str] = Form(None),
    message_request: Optional[str] = Form(None),
    response_language: Optional[TranslationEnum] = Form(None),
    model: Optional[str] = Form(None),
    output_format: Optional[str] = Form(None),
    file_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    logger.info(f"Received request for action: {action}")
    # Validate file type
    if file:
        logger.info(f"Received file: {file.filename}")
        file_ext = "." + file.filename.split(".")[-1].lower()
        if file_ext not in allowed_extensions:
            return RTASErrorResponseModel(
                status="error",
                action=action.value,
                error_message="Invalid file format. Only .pdf and .docx are supported.",
                error_code=400,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        try:
            # Validate file size (max 10MB)
            file_bytes = await file.read()
            file_size = len(file_bytes)  # Read file to check size
            await file.seek(0)  # Reset pointer after reading
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise HTTPException(status_code=500, detail="Error processing the file")

        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return RTASErrorResponseModel(
                status="error",
                action=action.value,
                error_message="File size exceeds the 10MB limit.",
                error_code=400,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        doc_context = await fast_file_process_object.get_markdown_with_pymupdf4llm(file)
    else:
        logger.info("No file uploaded.")

        if document_id and file_name:
            with app.state.db.get_session() as session:
                repo = DocumentRepository(session)
                document = await repo.get_document_by_id_and_file_name(document_id, file_name)
                if not document:
                    return RTASErrorResponseModel(
                        status="error",
                        action=action.value,
                        error_message=f"Document not found for doc_id '{document_id}' and file_name '{file_name}'.",
                        error_code=400,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    )
                doc_context = document.preprocessed_content
                logger.info(f"Loaded document content from DB for doc_id: {document_id} and file_name: {file_name}")
        else:
            if not processed_content:
                return RTASErrorResponseModel(
                    status="error",
                    action=action.value,
                    error_message="Either 'file' must be uploaded, or provide both 'document_id' and 'file_name', or provide 'processed_content'.",
                    error_code=400,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            doc_context = processed_content

    # Check if 'text' is required for 'summarize' or 'translate'
    if not account_id:
        return RTASErrorResponseModel(
            status="error",
            action=action.value,
            error_message="The 'account_id' parameter is required.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    if action == RealTimeActionEnum.chat:
        if not message_request:
            return RTASErrorResponseModel(
                status="error",
                action=action.value,
                error_message="The 'message_request' parameter is required when action is 'chat'.",
                error_code=400,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        if not chat_id or chat_id == '':
            chat_id = str(uuid.uuid4())
    elif action == RealTimeActionEnum.translate:
        if not response_language:
            return RTASErrorResponseModel(
                status="error",
                action=action.value,
                error_message="The 'response_language' parameter is required when action is 'translate'.",
                error_code=400,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

    try:
        # Align action to prompt_type
        prompt_type = action.value  # 'summarize', 'translate', 'chat'
        with app.state.db.get_session() as session:
            # Call Azure OpenAI model to process data
            if prompt_type == "chat":
                chat_repo = ChatRecordRepository(session)
                try:
                    # 取得歷史紀錄與 sequence
                    logger.info(f"Start chat process...")
                    chat_exists = await chat_repo.check_chat_id_exists(chat_id)
                    histories = await chat_repo.get_history_by_chat_id(chat_id) if chat_exists else []
                    latest_sequence = await chat_repo.get_latest_sequence(chat_id) or 0
                    logger.info(f"Getting chat histories...")
                    chat_histories = chat_use_case_object.build_context_from_history(
                        histories=histories,
                        sequence=latest_sequence,
                        window=10
                    )
                    logger.info(f"Sending chat prompt...")
                    # 送出 prompt，帶入上下文
                    response = await sys_prompt_object.set_real_time_prompt(
                        context=doc_context,
                        prompt_type=prompt_type,
                        message_request=message_request,
                        chat_history=chat_histories
                    )
                    logger.info(f"Saving chat record...")
                    # 新增 USER 訊息
                    await chat_repo.insert_message(
                        ChatRecordCreate(
                            chat_id=chat_id,
                            role=RoleEnum.user,
                            message=message_request
                        )
                    )

                    # 新增 AI 回覆訊息
                    await chat_repo.insert_message(
                        ChatRecordCreate(
                            chat_id=chat_id,
                            role=RoleEnum.ai,
                            message=response["response"]
                        )
                    )
                except Exception as e:
                    logger.error(f"[chat] Failed during DB or prompt handling: {e}")
                    return RTASErrorResponseModel(
                        status="error",
                        action=action.value,
                        error_message=str(e),
                        error_code=500,
                        timestamp=datetime.utcnow().isoformat() + "Z"
                    )

            elif prompt_type == "translate":
                logger.info(f"Sending translate prompt...")
                response = await sys_prompt_object.set_real_time_prompt(
                    context=doc_context,
                    prompt_type=prompt_type,
                    response_language=response_language
                )
            else:
                logger.info(f"Sending summarize prompt...")
                response = await sys_prompt_object.set_real_time_prompt(
                    context=doc_context,
                    prompt_type=prompt_type
                )
            result = response["response"]
    except Exception as e:
        logger.exception("Error during prompt processing")
        return RTASErrorResponseModel(
            status="error",
            action=action.value,
            error_message=str(e),
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    return RTASSuccessResponseModel(
        status="success",
        action=action.value,
        account_id=account_id,
        chat_id=chat_id,
        message_request=message_request,
        message_response=result,
        file_name=file_name,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

@app.post("/delete_record", responses={
    200: {"model": DRSuccessResponseModel},
    400: {"model": DRErrorResponseModel},
    500: {"model": DRErrorResponseModel}
})
async def delete_record(
    system_name: SystemEnum= Form(...),
    document_id: str = Form(...),
    file_name: str = Form(...)
):
    db_session = app.state.db.get_session()
    try:
        # 初始化 Repository 與 UseCase
        repo = DocumentRepository(db_session)

        deleted = await repo.delete_document_id_and_file_name(document_id, file_name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

        await ai_search_use_case_object.delete_document_by_id_and_file_name(document_id, file_name)

        return DRSuccessResponseModel(
            status="success",
            document_id=document_id,
            file_name = file_name,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Delete record failed: {e}")
        return DRErrorResponseModel(
            status="error",
            document_id=document_id,
            file_name=file_name,
            error_message=str(e),
            error_code=404,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    finally:
        db_session.close()

@app.post("/expired_contract_preprocess", responses={
    200: {"model": ASSuccessResponseModel},
    400: {"model": ASErrorResponseModel},
    500: {"model": ASErrorResponseModel}
})
async def expired_contract_preprocess(
    system_name: SystemEnum = Form(...),
    account_id: str = Form(...),
    document_id: str = Form(...),
    file: UploadFile = File(...)
):

    logger.info(f"Receiving expired file: {file.filename}...")

    # Validate file type
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        return EXCPErrorResponseModel(
            status="error",
            error_message="Invalid file format. Only .pdf and .docx are supported.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    try:
        # Validate file size (max 10MB)
        pdf_bytes = await file.read()
        file_size = len(pdf_bytes)  # Read file to check size
        await file.seek(0)  # Reset pointer after reading
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail="Error processing the file")

    if file_size > 10 * 1024 * 1024:  # 10MB limit
        return EXCPErrorResponseModel(
            status="error",
            error_message="File size exceeds the 10MB limit.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Check if 'text' is required for 'summarize' or 'translate'
    if not account_id:
        return EXCPErrorResponseModel(
            status="error",
            error_message="The 'account_id' parameter is required.",
            error_code=400,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    try:
        os.makedirs(SAVE_FILE_PATH, exist_ok=True)
        save_path = os.path.join(SAVE_FILE_PATH, file.filename)
        await file_process_object.save_upload_file(file, save_path)

        merged_bundle = await run_ai_service_pipeline()
        if not merged_bundle or merged_bundle.strip() == "":
            msg = f"Empty response from AI pipeline..."
            logger.error(msg)
            raise ValueError(msg)
    except Exception as e:
        logger.error(f"LLM service failed: {e}")
        return EXCPErrorResponseModel(
            status="error",
            error_message=f"Error while processing file: {file.filename}.",
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    preprocessed_data = merged_bundle
    # Insert contract record into DB
    session: Session = app.state.db.get_session()
    try:
        doc_repo = DocumentRepository(session)
        existing_doc = await doc_repo.get_document_by_id_and_file_name(document_id, file.filename)

        if existing_doc:
            old_ai_search_id = existing_doc.ai_search_id
            update_data = DocumentRecordUpdate(
                file_name=file.filename,
                preprocessed_content=preprocessed_data,
                translated_context=None,
                summarized_context=None,
                qna_context=None,
                updated_by=account_id
            )
            await doc_repo.update_document(document_id, update_data)

            await ai_search_use_case_object.delete_document(old_ai_search_id)
            await ai_search_use_case_object.upload_single_document(
                id=old_ai_search_id,
                file_id=document_id,
                file_name=file.filename,
                content=preprocessed_data
            )
        else:
            ai_search_id = str(uuid.uuid4())
            create_data = DocumentRecordCreate(
                doc_id=document_id,
                file_name=file.filename,
                ai_search_id=ai_search_id,
                doc_content=None,
                preprocessed_content=preprocessed_data,
                translated_context=None,
                summarized_context=None,
                qna_context=None,
                created_by=account_id,
                updated_by=account_id
            )
            await doc_repo.create_document(create_data)

            await ai_search_use_case_object.upload_single_document(
                id=ai_search_id,
                file_id=document_id,
                file_name=file.filename,
                content=preprocessed_data
            )

    except Exception as e:
        logger.error(f"DB insert error: {e}")
        return EXCPErrorResponseModel(
            status="error",
            error_message="Internal server error when saving result to DB.",
            error_code=500,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    finally:
        session.close()

    return EXCPSuccessResponseModel(
        status="success",
        action=None,
        account_id=account_id,
        document_id=document_id,
        message_response=ExpiredContractResultModel(
            processed_content=preprocessed_data
        ),
        file_name=file.filename,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/health_check")
async def health_check():
    return {"status": "Alive"}

async def handle_action(file: UploadFile):
    try:
        os.makedirs(SAVE_FILE_PATH, exist_ok=True)
        save_path = os.path.join(SAVE_FILE_PATH, file.filename)
        await file_process_object.save_upload_file(file, save_path)

        merged_bundle = await run_ai_service_pipeline()
        if not merged_bundle or merged_bundle.strip() == "":
            msg = f"Empty response from Document Intelligence pipeline"
            logger.error(msg)
            raise ValueError(msg)
        return merged_bundle
    except Exception as e:
        logger.exception(f"Exception in handle_action(): {e}")
        raise RuntimeError(f"handle_action failed during Document Intelligence pipeline: {e}")

if __name__ == '__main__':
    uvicorn.run(
        app="main:app",
        host=os.getenv('APP_SERVER_HOST'),
        port=int(os.getenv('APP_SERVER_PORT')),
        workers=int(os.getenv('APP_SERVER_WORKER')),
    )