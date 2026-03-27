import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.domain.models.outbox import Outbox
from backend.domain.services.outbox_service import OutboxService
from backend.domain.schemas.payment import OutboxMessage

logger = logging.getLogger(__name__)

# Database setup
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class OutboxWorker:
    def __init__(self, poll_interval: int = 2):
        self.poll_interval = poll_interval
        self.running = True
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    async def publish_message(self, outbox: Outbox) -> bool:
        """Публикация сообщения в RabbitMQ"""
        try:
            # Ensure queue exists
            queue = await self.channel.declare_queue("payments.new", durable=True)

            # Publish message
            await self.channel.default_exchange.publish(
                Message(
                    body=json.dumps(outbox.payload).encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json"
                ),
                routing_key=queue.name
            )
            logger.info(f"Published outbox message {outbox.id} for payment {outbox.aggregate_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish outbox message {outbox.id}: {e}")
            return False

    async def process_outbox_messages(self, session: AsyncSession):
        """Обработка сообщений из outbox"""
        service = OutboxService(session)

        messages = await service.get_pending_messages(limit=100)

        if messages:
            logger.info(f"Found {len(messages)} pending outbox messages")

        for message in messages:
            # Publish to RabbitMQ
            success = await self.publish_message(message)

            if success:
                await service.mark_as_sent(message.id)
                await session.commit()
                logger.info(f"Outbox message {message.id} marked as sent")
            else:
                await service.mark_as_failed(message.id, "Publish failed")
                await session.commit()
                logger.warning(f"Outbox message {message.id} marked as failed")

    async def run(self):
        """Основной цикл worker"""
        logger.info(f"Starting outbox worker (poll interval: {self.poll_interval}s)")

        # Connect to RabbitMQ
        self.connection = await connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()

        # Ensure queue exists
        await self.channel.declare_queue("payments.new", durable=True)

        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    await self.process_outbox_messages(session)
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in outbox worker: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Остановка worker"""
        self.running = False


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    worker = OutboxWorker(poll_interval=settings.outbox_poll_interval)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Shutting down outbox worker...")
        worker.stop()
        if worker.connection:
            await worker.connection.close()


if __name__ == "__main__":
    asyncio.run(main())