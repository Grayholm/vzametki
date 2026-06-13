class AppError(Exception):
    status_code: int = 500
    user_message: str = "Что-то пошло не так. Попробуй позже."

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if user_message is not None:
            self.user_message = user_message
        if status_code is not None:
            self.status_code = status_code


class GroqAPIError(AppError):
    status_code = 502
    user_message = "Сервис ИИ временно недоступен. Проверь VPN и API-ключ Groq."


class GroqResponseParseError(AppError):
    status_code = 502
    user_message = "ИИ вернул некорректный ответ. Попробуй ещё раз."


class EmbeddingError(AppError):
    status_code = 500
    user_message = "Не удалось подготовить текст для поиска."