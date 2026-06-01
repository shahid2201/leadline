from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.session import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, data: dict[str, Any]) -> Session:
        record = Session(tenant_id=tenant_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str, session_id: str) -> Session | None:
        stmt = select(Session).where(Session.id == session_id, Session.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str) -> list[Session]:
        stmt = (
            select(Session)
            .where(Session.tenant_id == tenant_id)
            .order_by(Session.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: Session, data: dict[str, Any]) -> Session:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: Session) -> None:
        await self.session.delete(record)
        await self.session.flush()


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, session_id: str, data: dict[str, Any]) -> Message:
        record = Message(tenant_id=tenant_id, session_id=session_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str, message_id: str) -> Message | None:
        stmt = select(Message).where(Message.id == message_id, Message.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_session(self, tenant_id: str, session_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.tenant_id == tenant_id, Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: Message, data: dict[str, Any]) -> Message:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: Message) -> None:
        await self.session.delete(record)
        await self.session.flush()
