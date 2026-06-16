# Vzametki

Личное приложение для заметок с AI-классификацией, семантическим поиском и Telegram-ботом.

**Стек:** FastAPI, PostgreSQL (async), Qdrant (векторная БД), Redis (кэш + rate limit), RabbitMQ (асинхронные события), Groq API (LLM), aiogram, Docker, Alembic.

---

## Архитектура

```
Telegram Bot → API Gateway (HTTP) → notes-service → RabbitMQ (note.created/updated/deleted) → qdrant-service → Qdrant
                                        ↓
                                  ai-service (HTTP)
                                   / classify
                                   / generate-metadata
                                   / embed
```

### Микросервисы

| Сервис | Порт | Назначение |
|--------|------|------------|
| **api-gateway** | 8080 | Единая точка входа, прокси к сервисам |
| **notes-service** | 8001 | CRUD заметок (Postgres), бизнес-логика, публикация событий в RabbitMQ |
| **ai-service** | 8002 | Классификация (Groq), генерация метаданных, эмбеддинги (BGE) |
| **qdrant-service** | 8003 | Векторный поиск (Qdrant), консьюмер событий RabbitMQ |
| **bot-service** | — | Telegram бот (aiogram) |

### Асинхронное взаимодействие (RabbitMQ)

- **Exchange:** `notes.events` (topic)
- **Очередь:** `qdrant-service.queue` (bind на `note.*`)
- **События:**
  - `note.created` — создание заметки → qdrant-service векторизует и сохраняет
  - `note.updated` — обновление заметки → qdrant-service обновляет вектор
  - `note.deleted` — удаление заметки → qdrant-service удаляет вектор

Синхронные HTTP-вызовы (ai-service) остаются внутри консьюмера для получения эмбеддингов.

---

## Возможности

- **AI-классификация** — Groq определяет тип сообщения: заметка, идея, шум, поиск, запрос списка и т.д.
- **Авто-генерация** — для каждой заметки LLM создаёт заголовок и краткое содержание
- **Семантический поиск** — поиск по смыслу через embeddings (BGE) + Qdrant
- **REST API** — FastAPI с полным набором эндпоинтов
- **Telegram Bot** — отправляй сообщения в бота, и они автоматически сохраняются
- **Кэширование** — Redis для быстрого доступа к заметкам
- **Rate limiting** — защита от спама через Redis
- **Асинхронные события** — RabbitMQ для слабосвязанного взаимодействия сервисов

---

## Быстрый старт (локально)

> Нужен VPN, если Groq API или HuggingFace модели недоступны в регионе.

### 1. Переменные окружения

Создай `.env.dev` в корне проекта (см. образец ниже):

```env
MODE=dev
LOG_LEVEL=INFO
EXCHANGE_NAME=notes.events

# Postgres
POSTGRES_USER=vzametki
POSTGRES_PASSWORD=vzametki
POSTGRES_DB=vzametki
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=vzametki-redis
REDIS_PORT=6379
REDIS_DB=0

# Qdrant
QDRANT_HOST=vzametki-qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=
QDRANT_SCHEME=http

# RabbitMQ
RABBITMQ_HOST=vzametki-rabbitmq
RABBITMQ_PORT=5672

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Groq
GROQ_API_KEY=your_groq_api_key
GROQ_NOTE_GENERATION_MODEL=llama-3.3-70b-versatile

# === URL-ы внутренних сервисов (для Docker) ===
API_GATEWAY_URL=http://vzametki-api-gateway:8080
SERVICE_NOTES_URL=http://vzametki-notes-service:8001
AI_SERVICE_URL=http://vzametki-ai-service:8002
QDRANT_SERVICE_URL=http://vzametki-qdrant-service:8003

BOT_RATE_LIMIT_MESSAGES=5
BOT_RATE_LIMIT_SECONDS=60

FASTAPI_URL=http://vzametki-api-gateway:8080
```

### 2. Запуск через Docker (все сервисы + БД)

```bash
docker compose --env-file .env.dev up -d --build
```

API Gateway будет доступен по адресу `http://localhost:8080`, документация — `http://localhost:8080/docs`.

> **Важно:** Groq из контейнера может не видеть VPN с Windows. Если получаешь 403 — запускай API и бота на хосте, а в Docker оставь только инфраструктуру (`postgres`, `redis`, `qdrant`, `rabbitmq`).

---

## Структура проекта

```
vzametki/
├── services/
│   ├── api-gateway/               # Единая точка входа
│   │   └── src/
│   │       ├── main.py           # FastAPI с прокси-роутами
│   │       ├── config.py         # Pydantic settings
│   │       └── routers/
│   │           └── proxy.py      # Прокси к сервисам
│   │
│   ├── notes-service/            # CRUD заметок + продюсер RabbitMQ
│   │   └── src/
│   │       ├── main.py           # FastAPI + lifespan (Redis, RabbitMQ)
│   │       ├── exceptions.py     # AppError, NoteStorageError
│   │       ├── api/
│   │       │   ├── routers.py    # REST эндпоинты
│   │       │   └── exception_handlers.py
│   │       ├── core/
│   │       │   ├── service.py    # Бизнес-логика
│   │       │   ├── schemas.py    # Pydantic схемы
│   │       │   ├── models.py     # SQLAlchemy модель
│   │       │   └── repository.py # Слой данных
│   │       ├── infrastructure/
│   │       │   ├── config.py     # Pydantic settings
│   │       │   ├── db.py         # SQLAlchemy engine
│   │       │   └── redis.py      # Redis manager
│   │       └── messaging/
│   │           ├── events.py     # NoteEvent dataclass
│   │           └── producer.py   # Публикация событий в RabbitMQ
│   │
│   ├── ai-service/               # AI-обработка (Groq + BGE)
│   │   └── src/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── exceptions.py     # GroqAPIError, EmbeddingError
│   │       ├── groq_client.py    # Groq API клиент
│   │       ├── groq_errors.py    # Обработка ошибок Groq
│   │       ├── embedding.py      # BGE эмбеддинги (fastembed)
│   │       ├── prompts.py        # Промпты для LLM
│   │       ├── api/
│   │       │   ├── routers.py    # HTTP эндпоинты
│   │       │   └── exception_handlers.py
│   │       └── messaging/
│   │
│   ├── qdrant-service/           # Векторный поиск + консьюмер RabbitMQ
│   │   └── src/
│   │       ├── main.py           # FastAPI + lifespan (RabbitMQ consumer)
│   │       ├── config.py
│   │       ├── exceptions.py
│   │       ├── api/
│   │       │   └── routers.py    # HTTP эндпоинты (search, list)
│   │       ├── core/
│   │       │   └── qdrant_client.py
│   │       └── messaging/
│   │           └── consumer.py   # Приём событий из RabbitMQ
│   │
│   └── bot-service/              # Telegram бот
│       └── src/
│           ├── main.py           # Точка входа aiogram
│           ├── config.py         # Bot + Dispatcher + Redis rate limit
│           ├── handlers/
│           │   ├── router.py     # Обработчики сообщений
│           │   ├── handlers.py   # HTTP-клиент к API Gateway
│           │   └── states.py     # FSM состояния
│           └── middlewares/
│               └── rate_limit.py # Rate limiting на Redis
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Фикстуры-заглушки (моки)
│   ├── test_service.py           # Юнит-тесты (32 теста)
│   └── integration/
│       ├── __init__.py
│       ├── conftest.py           # Проверка MODE=test + setup БД
│       └── test_integration_service.py
│
├── infra/                        # Конфиги инфраструктуры
│   └── rabbitmq/
│       └── definitions.json      # RabbitMQ exchange/queue definitions
│
├── docker-compose.yml            # Все сервисы + инфраструктура
├── .env.dev                      # Переменные окружения
├── pyproject.toml
├── alembic.ini
└── README.md
```

---

## Тестирование

### Юнит-тесты (без БД, с моками)

Запускаются в любом окружении, Docker не нужен:

```bash
python -m pytest tests/test_service.py -v
```

Что покрывают (32 теста):

| Класс | Тестов | Что проверяет |
|---|---|---|
| `TestClassifyText` | 6 (parametrize) | Все категории классификации (Note, Search, ListAll, GetById, Trash) |
| `TestGenerateMetadata` | 2 (parametrize) | Генерацию заголовка и краткого содержания |
| `TestCreateNote` | 7 | Успешное создание, ошибки БД, embedding, Qdrant |
| `TestSearchNotes` | 4 | Поиск с query, без query, ошибки embedding и Qdrant |
| `TestListAllNotes` | 4 | Список заметок, ошибки Qdrant (AppError, RuntimeError, VectorStoreError) |
| `TestGetNoteById` | 6 | Получение из кэша и БД, not found, DatabaseError, AppError, неожиданная ошибка |
| `TestProcessText` | 3 | Создание заметки, поиск, trash |

### Интеграционные тесты (с реальной БД)

```bash
set MODE=test&& python -m pytest tests/integration/ -v
```

Перед запуском: подними Docker (`docker compose up -d postgres redis qdrant`) и накати миграции (`alembic upgrade head`).

---

## API Endpoints (API Gateway)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/notes/classify` | Классифицировать текст (без сохранения) |
| POST | `/notes/process` | Обработать и сохранить/найти заметку |
| GET | `/notes/{user_id}/list` | Список всех заметок пользователя |
| GET | `/notes/{user_id}/{note_id}` | Получить заметку по ID |
| PUT | `/notes/{user_id}/{note_id}` | Обновить заметку |
| DELETE | `/notes/{user_id}/{note_id}` | Удалить заметку |

### Пример: создать заметку

```bash
curl -X POST http://localhost:8080/notes/process \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345, "text": "Завтра нужно сделать доклад по биологии"}'
```

Ответ:
```json
{
  "category": "Note",
  "action": "created_note",
  "note": {
    "note_id": 1,
    "title": "Доклад по биологии",
    "summary": "Пользователь планирует сделать доклад по биологии завтра.",
    "category": "Note"
  }
}
```

### Пример: поиск

```bash
curl -X POST http://localhost:8080/notes/process \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345, "text": "Найди что я писал про биологию"}'
```

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `MODE` | `local`, `dev`, `test` — определяет `.env.{mode}` |
| `POSTGRES_*` | Подключение к PostgreSQL |
| `REDIS_*` | Подключение к Redis |
| `QDRANT_*` | Подключение к Qdrant |
| `RABBITMQ_*` | Подключение к RabbitMQ |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота |
| `GROQ_API_KEY` | API-ключ Groq |
| `GROQ_NOTE_GENERATION_MODEL` | Модель Groq (например `llama-3.3-70b-versatile`) |
| `AI_SERVICE_URL` | Внутренний URL ai-service |
| `API_GATEWAY_URL` | Внутренний URL API Gateway |
| `QDRANT_SERVICE_URL` | Внутренний URL qdrant-service |