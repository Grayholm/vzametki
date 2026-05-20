import asyncio
import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from src.database.config import settings
from src.exceptions import VectorStoreError


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
            except Exception as exc:
                if attempt == retries:
                    raise VectorStoreError(
                        f"Qdrant init failed after {retries} attempts: {exc}",
                    ) from exc

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
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(id=note_id, vector=vector, payload=payload),
                ],
            )
        except Exception as exc:
            logger.error("Qdrant upsert failed for note %s: %s", note_id, exc)
            raise VectorStoreError(
                f"Qdrant upsert failed for note {note_id}: {exc}",
            ) from exc

    async def search_similar_notes(
        self,
        user_id: int,
        vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        # Долбаный асинк, ля, сначала я написал единый запрос с точкой .points, 
        # но там он сначала вычисляет points синхронно, а такое нельзя сделать с корутигой
        try:
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id),
                        )
                    ]
                ),
                with_payload=True,
                limit=top_k,
            )
        except Exception as exc:
            logger.error("Qdrant search failed for user %s: %s", user_id, exc)
            raise VectorStoreError(
                f"Qdrant search failed for user {user_id}: {exc}",
            ) from exc

        search_result = result.points

        return [
            {"id": result.id, "payload": result.payload, "score": result.score}
            for result in search_result
        ]


qdrant_client = QdrantClient()
