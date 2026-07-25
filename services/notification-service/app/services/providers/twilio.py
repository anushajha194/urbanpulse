"""
Twilio implementation for the notification provider interface.
Stubs communication out to stdout if Twilio credentials are missing in config.
"""

import logging

from app.config import settings
from app.services.providers.base import BaseNotificationProvider

logger = logging.getLogger(__name__)


class TwilioProvider(BaseNotificationProvider):
    """Twilio client provider. Integrates with official Twilio SDK if credentials configured."""

    def __init__(self):
        self._client = None
        self._active = False

        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self._client = Client(
                    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
                )
                self._active = True
                logger.info("Twilio SMS client initialized and active.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}. Running in STUB mode.")

        if not self._active:
            logger.info("Twilio credentials missing. Running in STUB mode (stdout logging).")

    def send_sms(self, to_number: str, message: str) -> bool:
        """Sends SMS via Twilio API if active, otherwise logs mock details."""
        if self._active:
            try:
                self._client.messages.create(
                    body=message,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=to_number,
                )
                logger.info(f"Successfully sent SMS via Twilio to {to_number}")
                return True
            except Exception as e:
                logger.error(f"Failed to send SMS to {to_number} via Twilio: {e}")
                return False
        else:
            # Stub mode printout
            print(f"\n[MOCK SMS] to {to_number}:\n{message}\n")
            logger.info(f"Stub SMS logged for {to_number}")
            return True

    def send_whatsapp(self, to_number: str, message: str) -> bool:
        """Sends WhatsApp message via Twilio API if active, otherwise logs mock details."""
        whatsapp_to = f"whatsapp:{to_number}"
        whatsapp_from = f"whatsapp:{settings.TWILIO_FROM_NUMBER}"

        if self._active:
            try:
                self._client.messages.create(
                    body=message,
                    from_=whatsapp_from,
                    to=whatsapp_to,
                )
                logger.info(f"Successfully sent WhatsApp via Twilio to {to_number}")
                return True
            except Exception as e:
                logger.error(f"Failed to send WhatsApp to {to_number} via Twilio: {e}")
                return False
        else:
            # Stub mode printout
            print(f"\n[MOCK WHATSAPP] to {to_number}:\n{message}\n")
            logger.info(f"Stub WhatsApp logged for {to_number}")
            return True


twilio_provider = TwilioProvider()
