FROM python:3.13-slim

WORKDIR /app

COPY services/notes-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/notes-service/entrypoint.sh services/notes-service/entrypoint.sh
RUN chmod +x services/notes-service/entrypoint.sh

COPY services/notes-service/src/ ./services/notes-service/src/
COPY services/notes-service/migrations/ ./services/notes-service/migrations/
COPY alembic.ini ./alembic.ini

RUN mkdir -p services/notes-service/migrations/versions

ENTRYPOINT ["./services/notes-service/entrypoint.sh"]

EXPOSE 8001

CMD ["uvicorn", "services.notes-service.src.main:app", "--host", "0.0.0.0", "--port", "8001"]

