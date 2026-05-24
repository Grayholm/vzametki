# Vzametki

## Быстрый старт локально (запускать обязательно с VPN, если модели не доступны в регионе)

1. Переменные окружения — в `.env.local`, `MODE=local`.
2. Только инфраструктура (Postgres, Redis, Qdrant):
   ```bash
   docker compose --env-file (название вашего env файла) up -d
   ```
3. Миграции (один раз):
   ```bash
   set MODE=local&& alembic upgrade head
   ```
5. Два терминала:
   ```bash
   set MODE=local&& uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```
   ```bash
   set MODE=local&& python -m src.bot.main
   ```

## Запуск API и бота в Docker

Один `Dockerfile` на оба сервиса: у `api` команда по умолчанию (uvicorn), у `bot` — своя в `docker-compose.yml`.

Перед первым запуском примени миграции:
```bash
docker compose run --rm api alembic upgrade head
```

```bash
docker compose --env-file (название вашего env файла) --profile dev up -d --build
```


Важно: Groq из контейнера может не видеть VPN с Windows. Если снова 403 — запускай `api` и `bot` на хосте (см. выше), а в Docker оставь только БД.

## Описание проекта

Проект использует FastAPI и Groq API для классификации текста и генерации метаданных заметок. Также задействуются Redis и Qdrant для кеширования и семантического поиска.

## Основные компоненты

- `src/main.py` — точка входа FastAPI
- `src/api/routers/notes.py` — маршруты для работы с заметками
- `src/notes/service.py` — сервисная логика обработки текста и создания заметок
- `src/ai/groq_client.py` — клиент для обращения к Groq API
- `src/database/qdrant_client.py` — работа с Qdrant
- `src/database/redis_config.py` — кеширование в Redis

## Запуск проекта

1. Поднимите Docker-сервисы.
2. Запустите приложение с uvicorn.
3. Откройте доступ к API по адресу `http://localhost:8000`.
