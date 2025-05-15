from sqlalchemy.orm import Session
from app.repository.models.document import DocumentRecordModel
from app.enums.schema_enum import DocumentRecordCreate, DocumentRecordUpdate
from app.repository.database import Database


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, document: DocumentRecordCreate):
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

    def get_document(self, document_id: str):
        """Search doc_id in DocumentRecord"""
        return self.db.query(DocumentRecordModel).filter(DocumentRecordModel.doc_id == document_id).first()

    def get_document_by_file_name(self, file_name: str):
        """Search the first document record with matching file_name"""
        return self.db.query(DocumentRecordModel).filter(DocumentRecordModel.file_name == file_name).first()

    def get_document_by_id_and_file_name(self, document_id: str, file_name: str):
        """Search document by both document_id and file_name"""
        return (
            self.db.query(DocumentRecordModel)
            .filter(
                DocumentRecordModel.doc_id == document_id,
                DocumentRecordModel.file_name == file_name
            )
            .first()
        )

    def update_document(self, document_id: str, document: DocumentRecordUpdate):
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

    def delete_document(self, document_id: str):
        """Delete DocumentRecord"""
        document = self.db.query(DocumentRecordModel).filter(DocumentRecordModel.doc_id == document_id).first()
        if document:
            self.db.delete(document)
            self.db.commit()
            return True
        return False
