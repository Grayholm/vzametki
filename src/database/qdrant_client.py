from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.database.config import settings


client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.QDRANT_API_KEY)

async def init_qdrant():
    if not await client.collection_exists(collection_name="notes"):
        await client.create_collection(
            collection_name="notes",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

async def insert_note_vector(note_id: int, vector: list[float], payload: dict):
    await client.upsert(
        collection_name="notes",
        points=[
            PointStruct(id=note_id, vector=vector, payload=payload)
        ],
    )

async def search_similar_notes(vector: list[float], top_k: int = 5) -> list[dict]:
    search_result = await client.search(
        collection_name="notes",
        query_vector=vector,
        with_payload=True,
        limit=top_k,
    )
    return [{"id": res.id, "payload": res.payload, "score": res.score} for res in search_result]