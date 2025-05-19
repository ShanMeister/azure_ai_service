from sqlalchemy import create_engine, Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class DocumentRecordModel(Base):
    __tablename__ = 'nuecs_document_record'
    __table_args__ = {'schema': 'dbo'}

    doc_id = Column(VARCHAR(100), primary_key=True)
    file_name = Column(VARCHAR(100), index=True)
    ai_search_id = Column(Text)
    doc_content = Column(Text)
    preprocessed_content = Column(Text)
    translated_context = Column(Text)
    summarized_context = Column(Text)
    qna_context = Column(Text)
    created_by = Column(VARCHAR(100))
    created_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    updated_by = Column(VARCHAR(100))
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())