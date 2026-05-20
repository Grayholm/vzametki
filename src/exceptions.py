class AppError(Exception):
    """Базовая ошибка с сообщением для логов и для пользователя."""

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


class DatabaseError(AppError):
    status_code = 500
    user_message = "Ошибка при работе с базой данных."


class VectorStoreError(AppError):
    status_code = 503
    user_message = "Сервис поиска (Qdrant) недоступен. Проверь Docker."


class EmbeddingError(AppError):
    status_code = 500
    user_message = "Не удалось подготовить текст для поиска."


class NoteStorageError(AppError):
    status_code = 500
    user_message = "Заметка сохранена не полностью. Попробуй отправить текст снова."


class ApiClientError(AppError):
    status_code = 502
    user_message = "Сервер заметок недоступен. Убедись, что API запущен."
