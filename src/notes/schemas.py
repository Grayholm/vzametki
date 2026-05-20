from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    user_id: int
    full_text: str = Field(min_length=1)


class ProcessMessageRequest(BaseModel):
    user_id: int
    text: str = Field(min_length=1)
    category: str | None = None