import json

import httpx
from groq import AsyncGroq

from src.database.config import settings
from src.ai.prompts import (
    NOTE_METADATA_SYSTEM_PROMPT,
    NOTE_CLASSIFICATION_SYSTEM_PROMPT,
)


def _parse_json_from_llm(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        end = text.rfind("```")
        if end > 3:
            text = text[3:end].strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
    return json.loads(text)


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
        raw_content = response.choices[0].message.content
        print(f"Groq classification response: {raw_content}")

        try:
            parsed = _parse_json_from_llm(raw_content)
            category = parsed.get("category", "").strip()
        except json.JSONDecodeError:
            category = raw_content.strip().strip('"')

        return category

    async def generate_note_title_summary(self, content: str, category: str | None = None) -> dict[str, str]:
        prompt_content = content
        if category:
            prompt_content = f"Категория: {category}\n{content}"

        response = await self.client.chat.completions.create(
            model=settings.GROQ_NOTE_GENERATION_MODEL,
            messages=[
                {"role": "system", "content": NOTE_METADATA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_content}
            ]
        )
        print(f"Groq note generation response: {response}")
        try:
            return _parse_json_from_llm(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"Ошибка при разборе JSON от Groq: {e}")
            return {"title": "Ошибка генерации", "summary": "Не удалось создать конспект"}

    async def create_note(self, user_id: int, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{settings.FASTAPI_URL}/notes/",
                    json={"user_id": user_id, **payload},
                    timeout=10,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise e

    async def process_message(self, user_id: int, text: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{settings.FASTAPI_URL}/notes/process",
                    json={"user_id": user_id, "text": text},
                    timeout=10,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise e

    async def search_notes(self, query: str):
        pass

groq_client = GroqClient()