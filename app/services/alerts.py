import asyncio
import logging
import os
from dataclasses import dataclass
from uuid import UUID

import httpx

from app.db.models import MonitorState

logger = logging.getLogger(__name__)
MAX_CONCURRENT_ALERTS = 5


@dataclass(frozen=True)
class StateAlert:
    monitor_id: UUID
    name: str
    url: str
    previous_state: MonitorState
    next_state: MonitorState


def _alert_content(alert: StateAlert) -> tuple[str, str] | None:
    if alert.next_state == MonitorState.DOWN:
        return (
            "monitor.down",
            f"🔴 **Monitor DOWN**\n**{alert.name}** ({alert.url}) failed 3 consecutive checks.",
        )
    if alert.previous_state == MonitorState.DOWN and alert.next_state == MonitorState.UP:
        return (
            "monitor.recovered",
            f"🟢 **Monitor recovered**\n**{alert.name}** ({alert.url}) passed 2 consecutive checks.",
        )
    return None


async def send_state_alerts(alerts: list[StateAlert]) -> None:
    """Send best-effort Discord alerts for down and recovered transitions."""
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url or not alerts:
        return

    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        logger.error("alert.delivery_skipped: ALERT_WEBHOOK_URL is not a Discord webhook")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_ALERTS)
    timeout = httpx.Timeout(5.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:

        async def send_one(alert: StateAlert) -> None:
            content = _alert_content(alert)
            if content is None:
                return
            event_name, message = content
            async with semaphore:
                try:
                    response = await client.post(
                        webhook_url,
                        json={
                            "content": message,
                            "allowed_mentions": {"parse": []},
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error(
                        "alert.delivery_failed",
                        extra={
                            "monitor_id": str(alert.monitor_id),
                            "event": event_name,
                            "status_code": exc.response.status_code,
                        },
                    )
                except httpx.RequestError:
                    # Do not log the exception: HTTP client errors can contain the
                    # webhook URL, which includes its secret token.
                    logger.error(
                        "alert.delivery_failed",
                        extra={
                            "monitor_id": str(alert.monitor_id),
                            "event": event_name,
                        },
                    )
                except Exception:
                    # A notification failure must not undo persisted check results
                    # or turn a successful scheduler run into an API failure.
                    logger.error(
                        "alert.delivery_failed",
                        extra={
                            "monitor_id": str(alert.monitor_id),
                            "event": event_name,
                        },
                    )

        await asyncio.gather(*(send_one(alert) for alert in alerts))
