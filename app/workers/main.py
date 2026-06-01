import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any, cast

import boto3
from botocore.client import BaseClient

from app.ai.pipeline import process_message_created_event
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal
from app.integrations.pipeline import process_integration_event
from app.models.failed_job import FailedJob
from app.observability.tracing import configure_tracing, traced_span
from app.routing.pipeline import process_routing_event
from app.sequence.pipeline import process_sequence_step_event, process_sequence_trigger_event

logger = logging.getLogger("leadline.worker")


def _build_sqs_client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url,
    )


def _event_handlers() -> dict[str, Callable[[dict[str, Any]], None]]:
    return {
        "message.created": handle_message_created,
        "lead.created": handle_lead_created,
        "lead.updated": handle_lead_updated,
        "lead.score_updated": handle_lead_score_updated,
        "sequence.trigger": handle_sequence_trigger,
        "sequence.step.execute": handle_sequence_step_execute,
        "integration.lead.created": handle_integration_lead_created,
        "integration.lead.updated": handle_integration_lead_updated,
        "integration.lead.score_updated": handle_integration_lead_score_updated,
        "integration.timeline.created": handle_integration_timeline_created,
    }


def handle_message_created(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_message_created"):
        asyncio.run(process_message_created_event(payload))


def handle_lead_created(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_lead_created"):
        asyncio.run(process_routing_event(payload))


def handle_lead_updated(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_lead_updated"):
        asyncio.run(process_routing_event(payload))


def handle_lead_score_updated(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_lead_score_updated"):
        asyncio.run(process_routing_event(payload))


def handle_sequence_trigger(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_sequence_trigger"):
        asyncio.run(process_sequence_trigger_event(payload))


def handle_sequence_step_execute(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_sequence_step_execute"):
        asyncio.run(process_sequence_step_event(payload))


def handle_integration_lead_created(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_integration_lead_created"):
        asyncio.run(process_integration_event(payload))


def handle_integration_lead_updated(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_integration_lead_updated"):
        asyncio.run(process_integration_event(payload))


def handle_integration_lead_score_updated(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_integration_lead_score_updated"):
        asyncio.run(process_integration_event(payload))


def handle_integration_timeline_created(payload: dict[str, Any]) -> None:
    with traced_span("worker.handle_integration_timeline_created"):
        asyncio.run(process_integration_event(payload))


_MAX_RETRIES = 3


async def _save_failed_job(
    queue_name: str,
    event_type: str,
    payload: dict[str, Any],
    error: str,
    attempts: int,
) -> None:
    tenant_id: str | None = payload.get("tenant_id")  # type: ignore[assignment]
    async with AsyncSessionLocal() as db:
        db.add(
            FailedJob(
                queue_name=queue_name,
                event_type=event_type,
                payload=payload,
                error=error[:4000],
                attempts=attempts,
                status="pending",
                tenant_id=tenant_id,
            )
        )
        await db.commit()


def poll_queue(
    client: BaseClient,
    queue_url: str,
    handlers: dict[str, Callable[[dict[str, Any]], None]],
) -> None:
    with traced_span("worker.poll_queue", {"queue.url": queue_url}):
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
            AttributeNames=["ApproximateReceiveCount"],
        )
        messages = response.get("Messages", [])
        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            body = message.get("Body", "{}")
            payload: dict[str, Any] = json.loads(body)
            event = str(payload.get("event", ""))
            attrs = message.get("Attributes", {})
            receive_count = int(attrs.get("ApproximateReceiveCount", 1))

            handler = handlers.get(event)
            if handler:
                try:
                    handler(payload)
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Worker handler failed",
                        extra={"event": event, "attempt": receive_count},
                    )
                    if receive_count >= _MAX_RETRIES:
                        # Exceeded retries — move to DLQ table and delete from queue
                        asyncio.run(
                            _save_failed_job(
                                queue_name=queue_url.split("/")[-1],
                                event_type=event,
                                payload=payload,
                                error=str(exc),
                                attempts=receive_count,
                            )
                        )
                        client.delete_message(
                            QueueUrl=queue_url, ReceiptHandle=receipt_handle
                        )
                    # else: do NOT delete — SQS will redeliver with backoff
                    continue
            else:
                logger.warning("No handler for queue event", extra={"event": event})

            client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing()

    queue_urls = [
        settings.sqs_ai_jobs_queue_url,
        settings.sqs_routing_jobs_queue_url,
        settings.sqs_email_jobs_queue_url,
        settings.sqs_sms_jobs_queue_url,
        settings.sqs_sequence_jobs_queue_url,
        settings.sqs_integration_jobs_queue_url,
    ]
    queue_urls = [url for url in queue_urls if url]

    if not queue_urls:
        logger.info("No queue URLs configured; worker exiting")
        return

    client = _build_sqs_client()
    handlers = _event_handlers()
    logger.info("Worker started", extra={"queue_count": len(queue_urls)})

    while True:
        for queue_url in queue_urls:
            try:
                poll_queue(
                    client=client,
                    queue_url=cast(str, queue_url),
                    handlers=handlers,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Queue polling error", extra={"queue_url": queue_url})
        time.sleep(1)


if __name__ == "__main__":
    main()
