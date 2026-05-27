# Vzametki

Личное приложение для заметок с AI-классификацией, семантическим поиском и Telegram-ботом.

**Стек:** FastAPI, PostgreSQL (async), Qdrant (векторная БД), Redis (кэш + rate limit), Groq API (LLM), aiogram, Docker, Alembic.

---

## Возможности

- **AI-классификация** — Groq определяет тип сообщения: заметка, идея, шум, поиск, запрос списка и т.д.
- **Авто-генерация** — для каждой заметки LLM создаёт заголовок и краткое содержание
- **Семантический поиск** — поиск по смыслу через embeddings (BGE) + Qdrant
- **REST API** — FastAPI с полным набором эндпоинтов
- **Telegram Bot** — отправляй сообщения в бота, и они автоматически сохраняются
- **Кэширование** — Redis для быстрого доступа к заметкам
- **Rate limiting** — защита от спама через Redis

---

## Быстрый старт (локально)

> Нужен VPN, если Groq API или HuggingFace модели недоступны в регионе.

### 1. Переменные окружения

Создай `.env.local` в корне проекта:

```env
MODE=local

POSTGRES_USER=vzametki
POSTGRES_PASSWORD=vzametki
POSTGRES_DB=vzametki
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=
QDRANT_SCHEME=http

TELEGRAM_BOT_TOKEN=your_bot_token
FASTAPI_URL=http://localhost:8000

GROQ_API_KEY=your_groq_api_key
GROQ_NOTE_GENERATION_MODEL=llama-3.3-70b-versatile
```

### 2. Запусти инфраструктуру (БД)

```bash
docker compose up -d postgres redis qdrant
```

### 3. Примени миграции

```bash
set MODE=local&& alembic upgrade head
```

### 4. Запусти сервисы (два терминала)

**Терминал 1 — API:**
```bash
set MODE=local&& uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Терминал 2 — Telegram бот:**
```bash
set MODE=local&& python -m src.bot.main
```

API будет доступен по адресу `http://localhost:8000`, документация — `http://localhost:8000/docs`.

---

## Запуск в Docker (полный)

```bash
docker compose --env-file .env.dev --profile dev up -d --build
```

Перед первым запуском примени миграции:

```bash
docker compose run --rm api alembic upgrade head
```

> **Важно:** Groq из контейнера может не видеть VPN с Windows. Если получаешь 403 — запускай API и бота на хосте, а в Docker оставь только БД.

---

## Структура проекта

```
vzametki/
├── src/
│   ├── main.py                         # Точка входа FastAPI
│   ├── exceptions.py                   # Иерархия кастомных ошибок
│   │
│   ├── api/
│   │   ├── dependency.py               # DI: get_db, get_notes_service, http_client
│   │   ├── exception_handlers.py
│   │   └── routers/
│   │       └── notes.py                # REST эндпоинты
│   │
│   ├── ai/
│   │   ├── groq_client.py              # Клиент для Groq API
│   │   ├── groq_errors.py              # Обработка ошибок Groq
│   │   └── prompts.py                  # Промпты для LLM
│   │
│   ├── bot/
│   │   ├── main.py                     # Точка входа бота
│   │   ├── config.py                   # Bot + Dispatcher
│   │   ├── handlers/
│   │   │   ├── router.py               # Обработчики сообщений
│   │   │   ├── handlers.py             # API-клиент для бота
│   │   │   └── states.py               # FSM состояния
│   │   └── middlewares/
│   │       └── rate_limit.py           # Rate limiting на Redis
│   │
│   ├── database/
│   │   ├── config.py                   # Pydantic settings (.env)
│   │   ├── db.py                       # SQLAlchemy engine + session
│   │   ├── embedding.py                # BGE embeddings (fastembed)
│   │   ├── qdrant_client.py            # Qdrant (векторный поиск)
│   │   └── redis_config.py             # Redis (кэш + rate limit)
│   │
│   ├── migrations/                     # Alembic
│   │   └── versions/
│   │
│   └── notes/
│       ├── models.py                   # SQLAlchemy модель
│       ├── schemas.py                  # Pydantic схемы
│       ├── repository.py               # Слой доступа к данным
│       └── service.py                  # Бизнес-логика
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Фикстуры-заглушки (моки)
│   ├── test_service.py                 # Юнит-тесты
│   └── integration/
│       ├── __init__.py
│       ├── conftest.py                 # Проверка MODE=test + setup БД
│       └── test_integration_service.py # Интеграционный тесты
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
└── README.md
```

---

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
set MODE=test && python -m pytest tests/integration/ -v
```

Перед запуском: подними Docker (`docker compose up -d postgres redis qdrant`) и накати миграции (`alembic upgrade head`).

---

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/notes/classify` | Классифицировать текст (без сохранения) |
| POST | `/notes/process` | Обработать и сохранить/найти заметку |
| GET | `/notes/{user_id}/list` | Список всех заметок пользователя |
| GET | `/notes/{user_id}/{note_id}` | Получить заметку по ID |

### Пример: создать заметку

```bash
curl -X POST http://localhost:8000/notes/process \
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
curl -X POST http://localhost:8000/notes/process \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345, "text": "Найди что я писал про биологию"}'
```

---

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `MODE` | `local`, `dev`, `test`, `prod` — определяет `.env.{mode}` |
| `POSTGRES_*` | Подключение к PostgreSQL |
| `REDIS_*` | Подключение к Redis |
| `QDRANT_*` | Подключение к Qdrant |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота |
| `FASTAPI_URL` | Адрес API (бот стучится к API) |
| `GROQ_API_KEY` | API-ключ Groq |
| `GROQ_NOTE_GENERATION_MODEL` | Модель Groq (например `llama-3.3-70b-versatile`) |