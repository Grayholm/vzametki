import json
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class NoteEvent:
    """Базовое событие заметки."""
    event_type: str  # note.created, note.updated, note.deleted
    note_id: int
    user_id: int
    title: str = ""
    summary: str = ""
    full_text: str = ""
    category: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteEvent":
        return cls(
            event_type=data.get("event_type", ""),
            note_id=data.get("note_id", 0),
            user_id=data.get("user_id", 0),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            full_text=data.get("full_text", ""),
            category=data.get("category", ""),
        )