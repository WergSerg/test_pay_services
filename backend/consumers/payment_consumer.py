import asyncio
import random
import json
import logging
from datetime import datetime
from typing import Optional

import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.domain.models.payment import PaymentStatus
from backend.domain.repositories.payment_repository import PaymentRepository
from backend.domain.services.webhook_service import WebhookService
from backend.domain.schemas.payment import WebhookPayload, OutboxMessage
from backend.core.exceptions import BusinessError, PaymentProcessingError

logger = logging.getLogger(__name__)


engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class PaymentConsumer:
    def __init__(self):
        self.webhook_service = WebhookService()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    async def emulate_payment_processing(self) -> bool:
        await asyncio.sleep(random.uniform(2, 5))
        if random.random() < 0.1:
            raise BusinessError("Payment declined by gateway")

        return True

    async def process_payment(self, message: OutboxMessage) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = PaymentRepository(session)

                payment = await repo.get_by_id(message.payment_id)
                if not payment:
                    logger.error(f"Payment {message.payment_id} not found")
                    return

                try:
                    success = await self.emulate_payment_processing()

                    if success:
                        status = PaymentStatus.SUCCEEDED
                    else:
                        status = PaymentStatus.FAILED

                    await repo.update_status(payment.id, status)
                    await session.commit()

                    webhook_payload = WebhookPayload(
                        payment_id=payment.id,
                        status=status,
                        amount=payment.amount,
                        currency=payment.currency,
                        description=payment.description,
                        processed_at=datetime.utcnow(),
                        metadata=payment.metadata_json
                    )

                    try:
                        await self.webhook_service.send_webhook(
                            payment.webhook_url,
                            webhook_payload
                        )
                        logger.info(f"Webhook sent for payment {payment.id}")
                    except Exception as e:
                        logger.error(f"Webhook failed for payment {payment.id}: {e}")

                except BusinessError as e:
                    logger.info(f"Business error for payment {payment.id}: {e}")
                    await repo.update_status(payment.id, PaymentStatus.FAILED)
                    await session.commit()

                except Exception as e:
                    logger.error(f"System error processing payment {payment.id}: {e}")
                    raise PaymentProcessingError(str(e))

    async def setup_queues(self):
        # Создаем основную очередь с DLX
        main_queue = await self.channel.declare_queue(
            "payments.new",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": "payments.new.dlq"
            }
        )
        logger.info("Created queue: payments.new")

        dlq_queue = await self.channel.declare_queue(
            "payments.new.dlq",
            durable=True
        )
        logger.info("Created queue: payments.new.dlq")

        return main_queue, dlq_queue

    async def handle_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                # Parse message
                body = json.loads(message.body.decode())
                outbox_message = OutboxMessage(**body)

                logger.info(f"Processing payment {outbox_message.payment_id}")

                # Process payment
                await self.process_payment(outbox_message)

                logger.info(f"Payment {outbox_message.payment_id} processed successfully")

            except BusinessError as e:
                logger.warning(f"Business error: {e}")

            except PaymentProcessingError as e:
                logger.error(f"System error, payment failed: {e}")

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                # Reject and requeue for unexpected errors
                await message.reject(requeue=True)

    async def run(self):
        logger.info("Starting payment consumer...")

        # Connect to RabbitMQ with retry
        retry_count = 0
        while retry_count < 5:
            try:
                self.connection = await connect_robust(settings.rabbitmq_url)
                self.channel = await self.connection.channel()
                logger.info("Connected to RabbitMQ")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Failed to connect to RabbitMQ (attempt {retry_count}/5): {e}")
                if retry_count < 5:
                    await asyncio.sleep(5)
                else:
                    raise

        # Setup queues
        main_queue, _ = await self.setup_queues()

        # Start consuming
        await main_queue.consume(self.handle_message)

        logger.info("Payment consumer is running. Waiting for messages...")

        try:
            await asyncio.Future()  # run forever
        except KeyboardInterrupt:
            logger.info("Shutting down consumer...")
            await self.connection.close()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    consumer = PaymentConsumer()
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())