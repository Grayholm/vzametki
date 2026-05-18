import asyncio
import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.database.config import settings


logger = logging.getLogger(__name__)


class QdrantClient:
    def __init__(
        self,
        collection_name: str = "notes",
        vector_size: int = 384,
        distance: Distance = Distance.COSINE,
    ) -> None:
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.QDRANT_API_KEY,
        )

    async def init_collection(self, retries: int = 5, delay_seconds: float = 2.0) -> None:
        for attempt in range(1, retries + 1):
            try:
                if await self.client.collection_exists(
                    collection_name=self.collection_name
                ):
                    return

                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance,
                    ),
                )
                return
            except Exception:
                if attempt == retries:
                    raise

                logger.warning(
                    "Qdrant is unavailable, retrying collection init (%s/%s)",
                    attempt,
                    retries,
                )
                await asyncio.sleep(delay_seconds)

    async def insert_note_vector(
        self,
        note_id: int,
        vector: list[float],
        payload: dict,
    ) -> None:
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(id=note_id, vector=vector, payload=payload),
            ],
        )

    async def search_similar_notes(
        self,
        vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        search_result = await self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            with_payload=True,
            limit=top_k,
        )

        return [
            {"id": result.id, "payload": result.payload, "score": result.score}
            for result in search_result
        ]


qdrant_client = QdrantClient()
