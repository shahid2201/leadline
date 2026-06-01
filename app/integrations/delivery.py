import logging

import boto3
from botocore.client import BaseClient
from twilio.rest import Client as TwilioClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DeliveryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._ses_client: BaseClient | None = None
        self._twilio_client: TwilioClient | None = None

    def _get_ses_client(self) -> BaseClient:
        if self._ses_client is None:
            self._ses_client = boto3.client(
                "ses",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                endpoint_url=self.settings.aws_endpoint_url,
            )
        return self._ses_client

    def _get_twilio_client(self) -> TwilioClient | None:
        if not self.settings.twilio_account_sid or not self.settings.twilio_auth_token:
            return None
        if self._twilio_client is None:
            self._twilio_client = TwilioClient(
                self.settings.twilio_account_sid,
                self.settings.twilio_auth_token,
            )
        return self._twilio_client

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        if not self.settings.ses_from_email:
            logger.info("SES sender not configured; email send skipped", extra={"to": to_email})
            return False

        ses = self._get_ses_client()
        ses.send_email(
            Source=self.settings.ses_from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        return True

    def send_sms(self, to_phone: str, body: str) -> bool:
        twilio = self._get_twilio_client()
        if not twilio or not self.settings.twilio_from_phone:
            logger.info("Twilio not configured; SMS send skipped", extra={"to": to_phone})
            return False

        twilio.messages.create(
            from_=self.settings.twilio_from_phone,
            to=to_phone,
            body=body,
        )
        return True
