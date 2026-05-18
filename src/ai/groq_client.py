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
        response = await self.client.chat.completions.create(
            model=settings.GROQ_FAST_MODEL,
            messages=[
                {"role": "system", "content": NOTE_CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ]
        )
        print(f"Groq classification response: {response}")
        return response.choices[0].message.content

    async def generate_note_title_summary(self, content: str) -> dict[str, str]:
        response = await self.client.chat.completions.create(
            model=settings.GROQ_NOTE_GENERATION_MODEL,
            messages=[
                {"role": "system", "content": NOTE_METADATA_SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ]
        )
        print(f"Groq note generation response: {response}")
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"Ошибка при разборе JSON от Groq: {e}")
            return {"title": "Ошибка генерации", "summary": "Не удалось создать конспект"}

    async def generate_note(self, content: str) -> dict:
        pass

groq_client = GroqClient()