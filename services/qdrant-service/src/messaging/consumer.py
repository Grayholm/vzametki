
import json
import logging
from typing import cast

import aio_pika
import httpx
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel

from src.config import settings
from src.core.qdrant_client import qdrant_client
from src.messaging.handlers import NoteEventHandler


logger = logging.getLogger(__name__)

QUEUE_NAME = "qdrant-service.queue"


class NoteEventConsumer:
    """Консьюмер событий заметок для qdrant-service."""

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None
        self._handler = NoteEventHandler()

    async def start(self) -> None:
        """Подключение к RabbitMQ и запуск consumer."""
        try:
            self._connection = await aio_pika.connect_robust(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
            self._channel = cast(AbstractRobustChannel, await self._connection.channel())
            await self._channel.set_qos(prefetch_count=1)

            # Объявляем exchange (должен совпадать с продюсером)
            exchange = await self._channel.declare_exchange(
                name=settings.EXCHANGE_NAME,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            # Объявляем очередь для qdrant-service
            queue = await self._channel.declare_queue(
                name=QUEUE_NAME,
                durable=True,
            )

            # Привязываем очередь ко всем событиям заметок
            routing_key = "note.*"
            await queue.bind(exchange, routing_key=routing_key)
            logger.info("Bound queue '%s' to '%s' with key '%s'", QUEUE_NAME, settings.EXCHANGE_NAME, routing_key)

            # Запускаем consumer
            await queue.consume(self._process_message)
            logger.info("Consumer started, waiting for events...")

        except Exception as exc:
            logger.error("Failed to start RabbitMQ consumer: %s", exc)
            raise

    async def _process_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """Обработка входящего сообщения."""
        async with message.process(ignore_processed=True):
            try:
                body = json.loads(message.body.decode())
                event_type = body.get("event_type")
                note_id = body.get("note_id")
                user_id = body.get("user_id")
                full_text = body.get("full_text")

                logger.info(
                    "Received event %s for note %s (user %s)",
                    event_type,
                    note_id,
                    user_id,
                )

                if event_type in ("note.created", "note.updated"):
                    await self._handler._handle_insert_update(body)
                elif event_type == "note.deleted":
                    await self._handler._handle_delete(note_id)
                else:
                    logger.warning("Unknown event type: %s", event_type)

            except Exception as exc:
                logger.error("Failed to process message: %s", exc)


consumer = NoteEventConsumer()