from pydantic import BaseModel


class CreateNoteRequest(BaseModel):
    user_id: int
    full_text: str


class ProcessMessageRequest(BaseModel):
    user_id: int
    text: str
    category: str | None = None