from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.session import Session
from app.repositories.conversation_repository import MessageRepository, SessionRepository
from app.repositories.lead_repository import LeadRepository
from app.services.plan_limit_service import PlanLimitService


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.messages = MessageRepository(db)
        self.leads = LeadRepository(db)
        self.plan_limits = PlanLimitService(db)

    async def create_session(self, tenant_id: str, payload: dict[str, Any]) -> Session:
        await self.plan_limits.enforce_session_creation_limit(tenant_id)
        data = dict(payload)
        if "metadata" in data:
            data["session_metadata"] = data.pop("metadata")
        record = await self.sessions.create(tenant_id=tenant_id, data=data)
        await self.db.commit()
        return record

    async def list_sessions(self, tenant_id: str) -> list[Session]:
        return await self.sessions.list(tenant_id=tenant_id)

    async def get_session(self, tenant_id: str, session_id: str) -> Session | None:
        return await self.sessions.get(tenant_id=tenant_id, session_id=session_id)

    async def update_session(
        self,
        tenant_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> Session | None:
        record = await self.sessions.get(tenant_id=tenant_id, session_id=session_id)
        if not record:
            return None
        data = dict(payload)
        if "metadata" in data:
            data["session_metadata"] = data.pop("metadata")
        updated = await self.sessions.update(record, data)
        await self.db.commit()
        return updated

    async def delete_session(self, tenant_id: str, session_id: str) -> bool:
        record = await self.sessions.get(tenant_id=tenant_id, session_id=session_id)
        if not record:
            return False
        await self.sessions.delete(record)
        await self.db.commit()
        return True

    async def attach_session_to_lead(
        self,
        tenant_id: str,
        lead_id: str,
        session_id: str,
    ) -> Session | None:
        lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            return None
        record = await self.sessions.get(tenant_id=tenant_id, session_id=session_id)
        if not record:
            return None
        updated = await self.sessions.update(record, {"lead_id": lead_id})
        await self.db.commit()
        return updated

    async def create_message(
        self,
        tenant_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> Message | None:
        await self.plan_limits.enforce_message_creation_limit(tenant_id)
        session_record = await self.sessions.get(tenant_id=tenant_id, session_id=session_id)
        if not session_record:
            return None
        message = await self.messages.create(
            tenant_id=tenant_id,
            session_id=session_id,
            data=payload,
        )
        await self.db.commit()
        return message

    async def list_messages(self, tenant_id: str, session_id: str) -> list[Message]:
        return await self.messages.list_for_session(tenant_id=tenant_id, session_id=session_id)

    async def get_message(self, tenant_id: str, message_id: str) -> Message | None:
        return await self.messages.get(tenant_id=tenant_id, message_id=message_id)

    async def update_message(
        self,
        tenant_id: str,
        message_id: str,
        payload: dict[str, Any],
    ) -> Message | None:
        record = await self.messages.get(tenant_id=tenant_id, message_id=message_id)
        if not record:
            return None
        updated = await self.messages.update(record, payload)
        await self.db.commit()
        return updated

    async def delete_message(self, tenant_id: str, message_id: str) -> bool:
        record = await self.messages.get(tenant_id=tenant_id, message_id=message_id)
        if not record:
            return False
        await self.messages.delete(record)
        await self.db.commit()
        return True
