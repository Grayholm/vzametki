import json

from groq import AsyncGroq

from src.database.config import settings
from src.ai.prompts import (
    NOTE_METADATA_SYSTEM_PROMPT,
    NOTE_CLASSIFICATION_SYSTEM_PROMPT,
)

class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def classify_note_content(self, content: str) -> str:
        pass

    async def generate_note_title_summary(self, content: str) -> dict[str, str]:
        pass

    async def generate_note(self, content: str) -> dict:
        pass

groq_client = GroqClient()