from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
from typing import List

from backend.domain.models.outbox import Outbox, OutboxStatus


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, outbox: Outbox) -> Outbox:
        self.session.add(outbox)
        await self.session.flush()
        return outbox

    async def get_pending_messages(self, limit: int = 100, max_attempts: int = 3) -> List[Outbox]:
        result = await self.session.execute(
            select(Outbox)
            .where(
                (Outbox.status == OutboxStatus.PENDING) |
                ((Outbox.status == OutboxStatus.FAILED) & (Outbox.attempts < max_attempts))
            )
            .order_by(Outbox.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_as_sent(self, outbox_id: UUID) -> None:
        await self.session.execute(
            update(Outbox)
            .where(Outbox.id == outbox_id)
            .values(
                status=OutboxStatus.SENT,
                processed_at=func.now()
            )
        )

    async def mark_as_failed(self, outbox_id: UUID, error: str) -> None:
        await self.session.execute(
            update(Outbox)
            .where(Outbox.id == outbox_id)
            .values(
                status=OutboxStatus.FAILED,
                last_error=error,
                attempts=Outbox.attempts + 1
            )
        )