from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any

from backend.domain.models.payment import PaymentStatus, Currency


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: Currency
    description: str = Field(..., min_length=1, max_length=500)
    metadata_json: Optional[Dict[str, Any]] = Field(None, alias="metadata_json")
    webhook_url: HttpUrl

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)


class PaymentResponse(BaseModel):
    id: UUID
    status: PaymentStatus
    created_at: datetime
    amount: Decimal
    currency: Currency
    description: str
    metadata_json: Optional[Dict[str, Any]]
    webhook_url: str
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class PaymentDetailResponse(PaymentResponse):
    idempotency_key: str


class WebhookPayload(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: Currency
    description: str
    processed_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None


class OutboxMessage(BaseModel):
    payment_id: UUID
    webhook_url: str
    amount: Decimal
    currency: Currency
    description: str
    metadata_json: Optional[Dict[str, Any]] = None
    idempotency_key: str