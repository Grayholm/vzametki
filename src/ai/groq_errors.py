import logging

from groq import APIConnectionError, APIStatusError, RateLimitError

from src.exceptions import GroqAPIError


logger = logging.getLogger(__name__)


def wrap_groq_error(exc: Exception, *, context: str) -> GroqAPIError:
    if isinstance(exc, APIStatusError):
        logger.error("Groq %s: status=%s body=%s", context, exc.status_code, exc.body)
        if exc.status_code == 403:
            return GroqAPIError(
                f"Groq forbidden during {context}",
                user_message="Доступ к Groq запрещён. Включи VPN (TUN) или проверь API-ключ.",
                status_code=502,
            )
        if exc.status_code == 429:
            return GroqAPIError(
                f"Groq rate limit during {context}",
                user_message="Слишком много запросов к ИИ. Подожди немного.",
                status_code=429,
            )
        return GroqAPIError(
            f"Groq API error during {context}: {exc}",
            user_message="Сервис ИИ вернул ошибку. Попробуй позже.",
            status_code=502,
        )

    if isinstance(exc, APIConnectionError):
        logger.error("Groq connection error during %s: %s", context, exc)
        return GroqAPIError(
            f"Groq connection error during {context}: {exc}",
            user_message="Нет связи с Groq. Проверь интернет и VPN.",
            status_code=502,
        )

    if isinstance(exc, RateLimitError):
        return GroqAPIError(
            f"Groq rate limit during {context}",
            user_message="Лимит запросов к ИИ исчерпан. Подожди немного.",
            status_code=429,
        )

    logger.exception("Unexpected Groq error during %s", context)
    return GroqAPIError(
        f"Unexpected Groq error during {context}: {exc}",
        user_message="Сервис ИИ временно недоступен.",
        status_code=502,
    )
