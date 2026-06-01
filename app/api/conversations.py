from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import get_auth_context
from app.db.session import get_db_session
from app.queue.sqs import QueueJob, SQSPublisher
from app.schemas.conversation import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/sessions", tags=["sessions"])
messages_router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=SessionResponse)
async def create_session(
    payload: SessionCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    service = ConversationService(db)
    record = await service.create_session(tenant_id=auth.tenant_id, payload=payload.model_dump())
    return SessionResponse.model_validate(record)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[SessionResponse]:
    service = ConversationService(db)
    records = await service.list_sessions(tenant_id=auth.tenant_id)
    return [SessionResponse.model_validate(item) for item in records]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    service = ConversationService(db)
    record = await service.get_session(tenant_id=auth.tenant_id, session_id=session_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return SessionResponse.model_validate(record)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    service = ConversationService(db)
    record = await service.update_session(
        tenant_id=auth.tenant_id,
        session_id=session_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return SessionResponse.model_validate(record)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = ConversationService(db)
    deleted = await service.delete_session(tenant_id=auth.tenant_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def create_message(
    session_id: str,
    payload: MessageCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    service = ConversationService(db)
    message = await service.create_message(
        tenant_id=auth.tenant_id,
        session_id=session_id,
        payload=payload.model_dump(),
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    publisher = SQSPublisher()
    publisher.publish(
        QueueJob(
            queue_name="ai_jobs",
            payload={
                "event": "message.created",
                "tenant_id": auth.tenant_id,
                "session_id": session_id,
                "message_id": message.id,
            },
        )
    )
    return MessageResponse.model_validate(message)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[MessageResponse]:
    service = ConversationService(db)
    messages = await service.list_messages(tenant_id=auth.tenant_id, session_id=session_id)
    return [MessageResponse.model_validate(item) for item in messages]


@messages_router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    service = ConversationService(db)
    message = await service.get_message(tenant_id=auth.tenant_id, message_id=message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
    return MessageResponse.model_validate(message)


@messages_router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: str,
    payload: MessageUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    service = ConversationService(db)
    message = await service.update_message(
        tenant_id=auth.tenant_id,
        message_id=message_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
    return MessageResponse.model_validate(message)


@messages_router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = ConversationService(db)
    deleted = await service.delete_message(tenant_id=auth.tenant_id, message_id=message_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
