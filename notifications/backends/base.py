"""Base email backend interface."""
from abc import ABC, abstractmethod


class EmailBackend(ABC):
    """Abstract base for email sending backends."""

    @abstractmethod
    def send(self, to_email: str, subject: str, body: str, **kwargs) -> str | None:
        """
        Send email. Returns provider_message_id if available, else None.
        Raises Exception on failure.
        """
        pass
