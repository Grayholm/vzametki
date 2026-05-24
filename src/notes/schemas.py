import datetime

from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    user_id: int
    full_text: str = Field(min_length=1)


class ProcessMessageRequest(BaseModel):
    user_id: int
    text: str = Field(min_length=1)
    category: str | None = None

class NoteSchema(BaseModel):
    id: int
    user_id: int
    title: str
    summary: str
    full_text: str
    created_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }