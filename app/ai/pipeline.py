from sqlalchemy import func, select

from app.ai.orchestrator import AIOrchestrator
from app.ai.scoring import compute_initial_scores
from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.models.lead_timeline_event import LeadTimelineEvent
from app.models.message import Message
from app.models.session import Session
from app.queue.sqs import QueueJob, SQSPublisher


async def process_message_created_event(payload: dict[str, str]) -> None:
    tenant_id = payload.get("tenant_id")
    session_id = payload.get("session_id")
    message_id = payload.get("message_id")

    if not tenant_id or not session_id or not message_id:
        return

    publisher = SQSPublisher()
    async with AsyncSessionLocal() as db:
        message_stmt = select(Message).where(
            Message.id == message_id,
            Message.tenant_id == tenant_id,
            Message.session_id == session_id,
        )
        message_result = await db.execute(message_stmt)
        message = message_result.scalar_one_or_none()
        if not message:
            return

        orchestrator = AIOrchestrator()
        understanding = await orchestrator.analyze_message(
            tenant_id=tenant_id,
            message_id=message_id,
            content=message.content,
        )

        message.intent = understanding.intent
        message.entities = understanding.entities
        message.sentiment = understanding.sentiment
        message.urgency = understanding.urgency
        message.topics = understanding.topics

        session_stmt = select(Session).where(
            Session.id == session_id,
            Session.tenant_id == tenant_id,
        )
        session_result = await db.execute(session_stmt)
        session_record = session_result.scalar_one_or_none()

        if session_record and session_record.lead_id:
            lead_stmt = select(Lead).where(
                Lead.id == session_record.lead_id,
                Lead.tenant_id == tenant_id,
            )
            lead_result = await db.execute(lead_stmt)
            lead = lead_result.scalar_one_or_none()

            if lead:
                count_stmt = select(func.count(Message.id)).where(
                    Message.tenant_id == tenant_id,
                    Message.session_id == session_id,
                )
                count_result = await db.execute(count_stmt)
                message_count = int(count_result.scalar_one())

                scores = compute_initial_scores(
                    understanding=understanding,
                    message_count=message_count,
                )
                lead.fit_score = scores.fit_score
                lead.engagement_score = scores.engagement_score
                lead.lead_score = scores.lead_score

                timeline_event = LeadTimelineEvent(
                    tenant_id=tenant_id,
                    lead_id=lead.id,
                    type="ai_scored",
                    payload={
                        "message_id": message.id,
                        "intent": understanding.intent,
                        "sentiment": understanding.sentiment,
                        "urgency": understanding.urgency,
                        "model": understanding.model,
                        "prompt_version": understanding.prompt_version,
                        "fit_score": scores.fit_score,
                        "engagement_score": scores.engagement_score,
                        "lead_score": scores.lead_score,
                    },
                )
                db.add(timeline_event)

        await db.commit()

        if session_record and session_record.lead_id:
            publisher.publish(
                QueueJob(
                    queue_name="routing_jobs",
                    payload={
                        "event": "lead.score_updated",
                        "tenant_id": tenant_id,
                        "lead_id": session_record.lead_id,
                    },
                )
            )
            publisher.publish(
                QueueJob(
                    queue_name="integration_jobs",
                    payload={
                        "event": "integration.lead.score_updated",
                        "tenant_id": tenant_id,
                        "lead_id": session_record.lead_id,
                    },
                )
            )
            publisher.publish(
                QueueJob(
                    queue_name="sequence_jobs",
                    payload={
                        "event": "sequence.trigger",
                        "tenant_id": tenant_id,
                        "lead_id": session_record.lead_id,
                        "trigger": "score_updated",
                    },
                )
            )
