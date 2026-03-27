import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from typing import Dict, Any
import logging

from backend.core.exceptions import WebhookDeliveryError
from backend.domain.schemas.payment import WebhookPayload

logger = logging.getLogger(__name__)


def is_retryable_exception(exception: Exception) -> bool:
    if isinstance(exception, WebhookDeliveryError):
        return True
    if isinstance(exception, httpx.TimeoutException):
        return True
    if isinstance(exception, httpx.NetworkError):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500
    return False


class WebhookService:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(is_retryable_exception),
        reraise=True
    )
    async def send_webhook(self, url: str, payload: WebhookPayload) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=payload.model_dump(mode="json"),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                logger.info(f"Webhook sent successfully to {url}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Webhook server error {e.response.status_code}, will retry")
                    raise WebhookDeliveryError(f"HTTP {e.response.status_code}")
                else:
                    logger.error(f"Webhook client error {e.response.status_code}, not retrying")
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(f"Webhook network error: {e}, will retry")
                raise WebhookDeliveryError(str(e))