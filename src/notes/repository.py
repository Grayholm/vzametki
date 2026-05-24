import logging

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.exceptions import DatabaseError
from src.notes.models import NotesModel


logger = logging.getLogger(__name__)


class NotesRepository:
    def __init__(self, session):
        self.session = session

    async def create_note(self, note_data):
        try:
            add_stmt = insert(NotesModel).values(**note_data).returning(NotesModel.id)
            result = await self.session.execute(add_stmt)
            return result.scalar_one()
        except IntegrityError as exc:
            await self.session.rollback()
            logger.error("Note integrity error: %s", exc)
            raise DatabaseError(
                f"Integrity error creating note: {exc}",
                user_message="Не удалось сохранить заметку: некорректные данные.",
            ) from exc
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Database error creating note: %s", exc)
            raise DatabaseError(
                f"Database error creating note: {exc}",
            ) from exc

    async def get_note_by_id(self, note_id):
        pass

    async def update_note(self, note_id, updated_data):
        pass

    async def delete_note(self, note_id):
        pass