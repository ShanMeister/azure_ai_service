from sqlalchemy import Column, Integer, VARCHAR, Enum, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.enums.chat_role_enum import RoleEnum

Base = declarative_base()

class ChatRecordModel(Base):
    __tablename__ = "nuecs_chat_record"
    __table_args__ = (
        UniqueConstraint("chat_id", "sequence", name="uq_chat_sequence"),
        {'schema': 'dbo'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(VARCHAR(100), nullable=False)
    sequence = Column(Integer, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

