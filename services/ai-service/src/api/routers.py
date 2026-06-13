import asyncio
import logging

from fastapi import APIRouter

from pydantic import BaseModel, Field

from src.embedding import embedding_manager
from src.groq_client import groq_client


logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai"])


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1)


class GenerateMetadataRequest(BaseModel):
    text: str = Field(min_length=1)
    category: str | None = None


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1)


@router.post("/classify")
async def classify_text(payload: ClassifyRequest) -> dict:
    """Классификация текста через Groq."""
    result = await groq_client.classify_note_content(payload.text)
    if isinstance(result, dict):
        return result
    return {"category": str(result).strip().strip('"')}


@router.post("/generate-metadata")
async def generate_metadata(payload: GenerateMetadataRequest) -> dict:
    """Генерация заголовка и summary через Groq."""
    result = await groq_client.generate_note_title_summary(
        payload.text, category=payload.category
    )
    return result


@router.post("/embed")
async def embed_text(payload: EmbedRequest) -> dict:
    """Генерация эмбеддинга (BGE) для текста."""
    vector = await asyncio.to_thread(embedding_manager.embed_text, payload.text)
    return {"vector": vector, "dimensions": len(vector)}