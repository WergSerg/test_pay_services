from sqlalchemy import Column, String, Numeric, Enum, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from enum import Enum as PyEnum

from backend.core.database import Base


class PaymentStatus(PyEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Currency(PyEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(Enum(Currency), nullable=False)
    description = Column(String(500), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    webhook_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_payments_status", "status"),
        Index("idx_payments_created_at", "created_at"),
    )