from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from src.models import NotesModel

class NotesRepository:
    def __init__(self, session):
        self.session = session

    async def create_note(self, note_data):
        try:
            add_stmt = insert(NotesModel).values(**note_data).returning(NotesModel.id)
            result = await self.session.execute(add_stmt)
            await self.session.commit()
            return result.scalar_one()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_note_by_id(self, note_id):
        pass

    async def update_note(self, note_id, updated_data):
        pass

    async def delete_note(self, note_id):
        pass

    async def search_notes(self, query):
        pass