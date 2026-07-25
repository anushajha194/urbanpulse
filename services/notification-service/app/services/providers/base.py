"""
Abstract Base class for SMS/WhatsApp notification providers.
Allows swapping providers (e.g. Twilio, AWS SNS) without modifying routing code.
"""

from abc import ABC, abstractmethod


class BaseNotificationProvider(ABC):
    """Notification service provider interface."""

    @abstractmethod
    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send SMS notification.
        """
        pass

    @abstractmethod
    def send_whatsapp(self, to_number: str, message: str) -> bool:
        """
        Send WhatsApp notification.
        """
        pass
