import httpx

from src.database.config import settings
        
async def process_message(user_id: int, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.FASTAPI_URL}/notes/process",
                json={
                    "user_id": user_id,
                    "text": text
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise e