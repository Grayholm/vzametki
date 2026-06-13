FROM python:3.13-slim

WORKDIR /app

COPY services/notes-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/notes-service/src/ ./src/
COPY services/notes-service/migrations/ ./migrations/
COPY alembic.ini ./alembic.ini

EXPOSE 8001

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8001"]