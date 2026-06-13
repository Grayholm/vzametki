import json
import logging

from groq import AsyncGroq

from src.config import settings
from src.groq_errors import wrap_groq_error
from src.prompts import (
    NOTE_CLASSIFICATION_SYSTEM_PROMPT,
    NOTE_METADATA_SYSTEM_PROMPT,
)


logger = logging.getLogger(__name__)


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
    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def classify_note_content(self, content: str) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model=settings.GROQ_NOTE_GENERATION_MODEL,
                messages=[
                    {"role": "system", "content": NOTE_CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
            )
        except Exception as exc:
            raise wrap_groq_error(exc, context="classification") from exc

        raw_content = response.choices[0].message.content or ""
        logger.info("Groq classification response: %s", raw_content)

        try:
            parsed = _parse_json_from_llm(raw_content)
            return parsed
        except json.JSONDecodeError:
            category = raw_content.strip().strip('"')
            return {"category": category}

    async def generate_note_title_summary(
        self, content: str, category: str | None = None
    ) -> dict[str, str]:
        prompt_content = content
        if category:
            prompt_content = f"Категория: {category}\n{content}"

        try:
            response = await self.client.chat.completions.create(
                model=settings.GROQ_NOTE_GENERATION_MODEL,
                messages=[
                    {"role": "system", "content": NOTE_METADATA_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content},
                ],
            )
        except Exception as exc:
            raise wrap_groq_error(exc, context="note metadata generation") from exc

        raw_content = response.choices[0].message.content or ""
        logger.info("Groq note generation response: %s", raw_content)

        try:
            return _parse_json_from_llm(raw_content)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse Groq metadata JSON: %s", exc)
            return {
                "title": "Ошибка генерации",
                "summary": "Не удалось создать конспект",
            }


groq_client = GroqClient()