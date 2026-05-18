import httpx

from src.database.config import settings


async def create_note(user_id: int, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.FASTAPI_URL}/notes/", 
                json={
                    "user_id": user_id,
                    "full_text": payload.get("full_text")
                }, 
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise e
        
async def search_notes(query: str):
    pass