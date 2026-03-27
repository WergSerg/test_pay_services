from sqlalchemy import Column, String, JSON, DateTime, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from backend.core.database import Base


class OutboxStatus:
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Outbox(Base):
    __tablename__ = "outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    aggregate_id = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default=OutboxStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_outbox_status", "status"),
        Index("idx_outbox_created_at", "created_at"),
    )