import httpx

from src.database.config import settings

CONFIRM_CATEGORIES = {"Note", "Idea", "Noise"}
PROCESS_TIMEOUT = 60.0


async def classify_message(user_id: int, text: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.FASTAPI_URL}/notes/classify",
            json={"user_id": user_id, "text": text},
            timeout=PROCESS_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["category"]


async def process_message(user_id: int, text: str, category: str | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        payload: dict = {"user_id": user_id, "text": text}
        if category is not None:
            payload["category"] = category
        response = await client.post(
            f"{settings.FASTAPI_URL}/notes/process",
            json=payload,
            timeout=PROCESS_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
