"""Common SQLAlchemy 2.0 async repository helpers."""
from typing import Any, Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")

class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session, self.model = session, model

    async def get(self, entity_id: Any) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelT, *, flush: bool = True) -> ModelT:
        self.session.add(entity)
        if flush:
            await self.session.flush()
        return entity

    async def delete(self, entity: ModelT, *, flush: bool = True) -> None:
        await self.session.delete(entity)
        if flush:
            await self.session.flush()

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.scalars(select(self.model).limit(limit).offset(offset))
        return list(result.all())
