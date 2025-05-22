from sqlalchemy.orm import Session
from typing import Optional, List
from app.repository.models.document import DocumentRecordModel
from app.repository.models.chat_record import ChatRecordModel
from app.enums.schema_enum import DocumentRecordCreate, DocumentRecordUpdate
from app.enums.schema_enum import ChatRecordCreate, ChatRecordUpdate
from app.enums.chat_role_enum import RoleEnum
from app.repository.database import Database


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    async def create_document(self, document: DocumentRecordCreate):
        """Build brand new DocumentRecord"""
        new_document = DocumentRecordModel(
            doc_id=document.doc_id,
            file_name=document.file_name,
            ai_search_id=document.ai_search_id,
            doc_content=document.doc_content,
            preprocessed_content=document.preprocessed_content,
            translated_context=document.translated_context,
            summarized_context=document.summarized_context,
            qna_context=document.qna_context,
            created_by=document.created_by,
            updated_by=document.updated_by
        )
        self.db.add(new_document)
        self.db.commit()
        self.db.refresh(new_document)
        return new_document

    async def get_document(self, document_id: str):
        """Search doc_id in DocumentRecord"""
        return self.db.query(DocumentRecordModel).filter(DocumentRecordModel.doc_id == document_id).first()

    async def get_document_by_file_name(self, file_name: str):
        """Search the first document record with matching file_name"""
        return self.db.query(DocumentRecordModel).filter(DocumentRecordModel.file_name == file_name).first()

    async def get_document_by_id_and_file_name(self, document_id: str, file_name: str):
        """Search document by both document_id and file_name"""
        return (
            self.db.query(DocumentRecordModel)
            .filter(
                DocumentRecordModel.doc_id == document_id,
                DocumentRecordModel.file_name == file_name
            )
            .first()
        )

    async def update_document(self, document_id: str, document: DocumentRecordUpdate):
        """Update exist DocumentRecord"""
        existing_document = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.doc_id == document_id).first()
        if existing_document:
            existing_document.file_name = document.file_name
            existing_document.doc_content = document.doc_content
            existing_document.preprocessed_content = document.preprocessed_content
            existing_document.translated_context = document.translated_context
            existing_document.summarized_context = document.summarized_context
            existing_document.updated_by = document.updated_by
            self.db.commit()
            self.db.refresh(existing_document)
            return existing_document
        return None

    async def delete_document(self, document_id: str):
        """Delete DocumentRecord"""
        document = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.doc_id == document_id).first()
        if document:
            self.db.delete(document)
            self.db.commit()
            return True
        return False

    async def delete_document_id_and_file_name(self, document_id: str, file_name: str) -> bool:
        """Delete DocumentRecord by document_id and file_name"""
        document = (
            self.db.query(DocumentRecordModel)
            .filter(
                DocumentRecordModel.doc_id == document_id,
                DocumentRecordModel.file_name == file_name
            )
            .first()
        )
        if document:
            self.db.delete(document)
            self.db.commit()
            return True
        return False

class ChatRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    async def check_chat_id_exists(self, chat_id: str) -> bool:
        count = (
            self.db.query(ChatRecordModel)
            .filter(ChatRecordModel.chat_id == chat_id)
            .count()
        )
        return count > 0

    async def get_history_by_chat_id(self, chat_id: str) -> List[ChatRecordModel]:
        return (
            self.db.query(ChatRecordModel)
            .filter(ChatRecordModel.chat_id == chat_id)
            .order_by(ChatRecordModel.sequence)
            .all()
        )

    async def get_by_id(self, record_id: int) -> Optional[ChatRecordModel]:
        return self.db.query(ChatRecordModel).filter_by(id=record_id).first()

    async def insert_message(self, payload: ChatRecordCreate) -> ChatRecordModel:
        sequence = await self.get_next_sequence(payload.chat_id)
        new_record = ChatRecordModel(
            chat_id=payload.chat_id,
            sequence=sequence,
            role=payload.role,
            message=payload.message
        )
        self.db.add(new_record)
        self.db.commit()
        self.db.refresh(new_record)
        return new_record

    async def update_message_by_id(self, record_id: int, payload: ChatRecordUpdate) -> Optional[ChatRecordModel]:
        record = await self.get_by_id(record_id)
        if record:
            if payload.message is not None:
                record.message = payload.message
            if payload.role is not None:
                record.role = payload.role
            self.db.commit()
            self.db.refresh(record)
        return record

    async def delete_message_by_id(self, record_id: int) -> bool:
        record = await self.get_by_id(record_id)
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False

    async def delete_history_by_chat_id(self, chat_id: str) -> int:
        deleted_count = (
            self.db.query(ChatRecordModel)
            .filter(ChatRecordModel.chat_id == chat_id)
            .delete()
        )
        self.db.commit()
        return deleted_count

    async def get_next_sequence(self, chat_id: str) -> int:
        last_entry = (
            self.db.query(ChatRecordModel)
            .filter(ChatRecordModel.chat_id == chat_id)
            .order_by(ChatRecordModel.sequence.desc())
            .first()
        )
        return (last_entry.sequence + 1) if last_entry else 1

    async def get_latest_sequence(self, chat_id: str) -> Optional[int]:
        last_entry = (
            self.db.query(ChatRecordModel)
            .filter(ChatRecordModel.chat_id == chat_id)
            .order_by(ChatRecordModel.sequence.desc())
            .first()
        )
        return last_entry.sequence if last_entry else None