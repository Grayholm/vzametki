from qdrant_client import QdrantClient

from src.database.config import settings


client = QdrantClient(url=settings.qdrant_url, api_key=settings.QDRANT_API_KEY)