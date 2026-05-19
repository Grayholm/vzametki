# Vzametki

## Быстрый старт локально

1. Убедитесь, что у вас есть все переменные окружения в `.env` или `.env.dev`.
2. Запустите контейнеры:
   ```bash
   docker-compose --env-file (название вашего env файла) up -d
   ```
3. Запустите приложение:
   ```bash
   set MODE=dev&& uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

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
