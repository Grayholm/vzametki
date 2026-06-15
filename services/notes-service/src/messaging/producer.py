import logging
from typing import cast

import aio_pika
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractRobustExchange

from src.infrastructure.config import settings
from src.messaging.events import NoteEvent


logger = logging.getLogger(__name__)


class NoteEventProducer:
    """Продюсер событий заметок в RabbitMQ."""

    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None
        self._exchange: AbstractRobustExchange | None = None

    async def connect(self) -> None:
        """Подключение к RabbitMQ и объявление exchange."""
        try:
            self._connection = await aio_pika.connect_robust(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
            self._channel = cast(AbstractRobustChannel, await self._connection.channel())
            # Объявляем topic exchange (если не существует — создастся)
            self._exchange = await self._channel.declare_exchange(
                name=settings.EXCHANGE_NAME,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            logger.info("Connected to RabbitMQ, exchange '%s' ready", settings.EXCHANGE_NAME)
        except Exception as exc:
            logger.warning("RabbitMQ connection failed: %s", exc)
            raise

    async def publish(self, event: NoteEvent) -> None:
        """Публикация события в exchange."""
        if self._exchange is None:
            logger.warning("Exchange not ready, skipping event %s", event.event_type)
            return

        try:
            message = Message(
                body=event.to_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            routing_key = event.event_type
            await self._exchange.publish(
                message=message,
                routing_key=routing_key,
            )
            logger.info(
                "Published event %s for note %s (user %s)",
                routing_key,
                event.note_id,
                event.user_id,
            )
        except Exception as exc:
            logger.error("Failed to publish event %s: %s", event.event_type, exc)

    async def close(self) -> None:
        """Закрытие соединения."""
        if self._connection:
            try:
                await self._connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as exc:
                logger.warning("RabbitMQ close failed: %s", exc)


# Глобальный экземпляр продюсера
producer = NoteEventProducer()
