from pydantic import BaseModel


class CreateNoteRequest(BaseModel):
    user_id: int
    full_text: str