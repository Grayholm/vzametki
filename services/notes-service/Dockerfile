FROM python:3.13-slim

WORKDIR /app

COPY services/notes-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы с сохранением структуры каталогов
COPY services/notes-service/src/ ./services/notes-service/src/
COPY services/notes-service/migrations/ ./services/notes-service/migrations/
COPY alembic.ini ./alembic.ini

EXPOSE 8001

# Корректируем путь запуска uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn services.notes-service.src.main:app --host 0.0.0.0 --port 8001"]
