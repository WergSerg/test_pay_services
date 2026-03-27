import json
from typing import List
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.outbox import Outbox
from backend.domain.repositories.outbox_repository import OutboxRepository
from backend.core.config import settings

logger = logging.getLogger(__name__)


class OutboxService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = OutboxRepository(session)

    async def get_pending_messages(self, limit: int = 100) -> List[Outbox]:
        return await self.repository.get_pending_messages(limit)

    async def mark_as_sent(self, outbox_id: str) -> None:
        await self.repository.mark_as_sent(outbox_id)

    async def mark_as_failed(self, outbox_id: str, error: str) -> None:
        await self.repository.mark_as_failed(outbox_id, error)