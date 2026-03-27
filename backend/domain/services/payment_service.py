from uuid import UUID
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.payment import Payment, PaymentStatus, Currency
from backend.domain.models.outbox import Outbox
from backend.domain.repositories.payment_repository import PaymentRepository
from backend.domain.repositories.outbox_repository import OutboxRepository
from backend.domain.schemas.payment import OutboxMessage
from backend.core.exceptions import BusinessError


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.outbox_repo = OutboxRepository(session)

    async def create_payment(
            self,
            idempotency_key: str,
            amount: Decimal,
            currency: Currency,
            description: str,
            webhook_url: str,
            metadata_json: Optional[Dict[str, Any]] = None
    ) -> Payment:
        existing = await self.payment_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        payment = Payment(
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            description=description,
            webhook_url=webhook_url,
            metadata_json=metadata_json,
            status=PaymentStatus.PENDING
        )

        payment = await self.payment_repo.create(payment)

        outbox_message = OutboxMessage(
            payment_id=payment.id,
            webhook_url=webhook_url,
            amount=amount,
            currency=currency,
            description=description,
            metadata_json=metadata_json,
            idempotency_key=idempotency_key
        )

        outbox = Outbox(
            event_type="payment.created",
            aggregate_id=str(payment.id),
            payload=outbox_message.model_dump(mode="json")
        )

        await self.outbox_repo.create(outbox)

        return payment

    async def get_payment(self, payment_id: UUID) -> Payment:
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise BusinessError("Payment not found")
        return payment

    async def update_payment_status(
            self,
            payment_id: UUID,
            status: PaymentStatus
    ) -> None:
        await self.payment_repo.update_status(payment_id, status)