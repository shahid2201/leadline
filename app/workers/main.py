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
    }


def handle_message_created(payload: dict[str, Any]) -> None:
    asyncio.run(process_message_created_event(payload))


def handle_lead_created(payload: dict[str, Any]) -> None:
    asyncio.run(process_routing_event(payload))


def handle_lead_updated(payload: dict[str, Any]) -> None:
    asyncio.run(process_routing_event(payload))


def handle_lead_score_updated(payload: dict[str, Any]) -> None:
    asyncio.run(process_routing_event(payload))


def handle_sequence_trigger(payload: dict[str, Any]) -> None:
    asyncio.run(process_sequence_trigger_event(payload))


def handle_sequence_step_execute(payload: dict[str, Any]) -> None:
    asyncio.run(process_sequence_step_event(payload))


def poll_queue(
    client: BaseClient,
    queue_url: str,
    handlers: dict[str, Callable[[dict[str, Any]], None]],
) -> None:
    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=10,
    )
    messages = response.get("Messages", [])
    for message in messages:
        receipt_handle = message["ReceiptHandle"]
        body = message.get("Body", "{}")
        payload: dict[str, Any] = json.loads(body)
        event = str(payload.get("event", ""))

        handler = handlers.get(event)
        if handler:
            handler(payload)
        else:
            logger.warning("No handler for queue event", extra={"event": event})

        client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

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
