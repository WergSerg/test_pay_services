from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import Optional
from datetime import datetime

from backend.domain.models.payment import Payment, PaymentStatus
from backend.core.exceptions import BusinessError


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        try:
            self.session.add(payment)
            await self.session.flush()
            await self.session.refresh(payment)
            return payment
        except IntegrityError as e:
            if "idempotency_key" in str(e).lower():
                raise BusinessError("Idempotency key already exists")
            raise

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def update_status(
            self,
            payment_id: UUID,
            status: PaymentStatus,
            processed_at: Optional[datetime] = None
    ) -> None:
        await self.session.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(
                status=status,
                processed_at=processed_at or datetime.utcnow()
            )
        )

    async def update_with_optimistic_lock(
            self,
            payment_id: UUID,
            status: PaymentStatus,
            expected_status: PaymentStatus,
            processed_at: Optional[datetime] = None
    ) -> bool:
        result = await self.session.execute(
            update(Payment)
            .where(
                Payment.id == payment_id,
                Payment.status == expected_status
            )
            .values(
                status=status,
                processed_at=processed_at or datetime.utcnow()
            )
        )
        return result.rowcount > 0

    async def get_pending_payments(
            self,
            limit: int = 100,
            older_than_minutes: int = 5
    ) -> list[Payment]:
        from sqlalchemy import func
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)

        result = await self.session.execute(
            select(Payment)
            .where(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at <= threshold
            )
            .order_by(Payment.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_payments_by_status(
            self,
            status: PaymentStatus,
            limit: int = 100,
            offset: int = 0
    ) -> list[Payment]:
        result = await self.session.execute(
            select(Payment)
            .where(Payment.status == status)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_payments_count_by_status(self, status: PaymentStatus) -> int:
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(Payment.id))
            .where(Payment.status == status)
        )
        return result.scalar_one()

    async def delete_old_payments(
            self,
            older_than_days: int = 30,
            statuses: list[PaymentStatus] = None
    ) -> int:
        from datetime import timedelta

        threshold = datetime.utcnow() - timedelta(days=older_than_days)

        query = delete(Payment).where(Payment.created_at <= threshold)

        if statuses:
            query = query.where(Payment.status.in_(statuses))

        result = await self.session.execute(query)
        return result.rowcount
