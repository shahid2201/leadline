import json
import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.client import BaseClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QueueJob:
    queue_name: str
    payload: dict[str, Any]


class SQSPublisher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._queue_urls = {
            "ai_jobs": self.settings.sqs_ai_jobs_queue_url,
            "routing_jobs": self.settings.sqs_routing_jobs_queue_url,
            "email_jobs": self.settings.sqs_email_jobs_queue_url,
            "sms_jobs": self.settings.sqs_sms_jobs_queue_url,
            "sequence_jobs": self.settings.sqs_sequence_jobs_queue_url,
            "integration_jobs": self.settings.sqs_integration_jobs_queue_url,
        }
        self._client: BaseClient | None = None

    def _get_client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "sqs",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                endpoint_url=self.settings.aws_endpoint_url,
            )
        return self._client

    def publish(self, job: QueueJob) -> bool:
        queue_url = self._queue_urls.get(job.queue_name)
        if not queue_url:
            logger.info(
                "Queue URL not configured; skipping publish",
                extra={"queue_name": job.queue_name},
            )
            return False

        client = self._get_client()
        client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(job.payload),
        )
        return True
