import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.db.models import CheckOutcome, CheckResult, Monitor
from app.db.session import SessionFactory
from app.services.checker import (
    MAX_CONCURRENT_CHECKS,
    MAX_DUE_MONITORS_PER_RUN,
    CheckObservation,
    check_monitor,
    make_http_client,
)
from app.services.state_machine import apply_observation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitorSnapshot:
    id: UUID
    method: str
    url: str
    timeout_ms: int


async def run_due_checks(force: bool = False) -> dict[str, int]:
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        query = select(Monitor).where(Monitor.enabled.is_(True))
        if not force:
            query = query.where(Monitor.next_check_at <= now)
        result = await session.execute(
            query.order_by(Monitor.next_check_at)
            .limit(MAX_DUE_MONITORS_PER_RUN)
            .with_for_update(skip_locked=True)
        )
        due_monitors = list(result.scalars().all())
        snapshots = [
            MonitorSnapshot(
                id=monitor.id,
                method=monitor.method,
                url=monitor.url,
                timeout_ms=monitor.timeout_ms,
            )
            for monitor in due_monitors
        ]
        for monitor in due_monitors:
            # Reserve this row briefly so a crashed run can be retried promptly.
            monitor.next_check_at = now + timedelta(seconds=60)
        await session.commit()

    if not snapshots:
        return {"claimed": 0, "checked": 0, "transitions": 0}

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    observations: list[tuple[MonitorSnapshot, CheckObservation]] = []
    async with make_http_client() as client:
        async def run_one(snapshot: MonitorSnapshot) -> None:
            # The checker only needs this small immutable snapshot, not an ORM session.
            async with semaphore:
                observation = await check_monitor(snapshot, client)
                observations.append((snapshot, observation))

        await asyncio.gather(*(run_one(snapshot) for snapshot in snapshots))

    transitions = 0
    async with SessionFactory() as session:
        for snapshot, observation in observations:
            result = await session.execute(
                select(Monitor)
                .where(Monitor.id == snapshot.id)
                .with_for_update()
            )
            monitor = result.scalar_one_or_none()
            if monitor is None:
                continue

            previous_state = monitor.current_state
            next_state, failures, successes = apply_observation(
                current_state=monitor.current_state,
                consecutive_failures=monitor.consecutive_failures,
                consecutive_successes=monitor.consecutive_successes,
                succeeded=observation.outcome == CheckOutcome.SUCCESS,
            )
            monitor.current_state = next_state
            monitor.consecutive_failures = failures
            monitor.consecutive_successes = successes
            monitor.next_check_at = observation.checked_at + timedelta(
                seconds=monitor.interval_seconds
            )
            session.add(
                CheckResult(
                    monitor_id=monitor.id,
                    checked_at=observation.checked_at,
                    latency_ms=observation.latency_ms,
                    status_code=observation.status_code,
                    outcome=observation.outcome,
                    error_detail=observation.error_detail,
                )
            )
            if previous_state != next_state:
                transitions += 1
                logger.info(
                    "monitor.state_changed",
                    extra={
                        "monitor_id": str(monitor.id),
                        "from_state": previous_state.value,
                        "to_state": next_state.value,
                    },
                )
        await session.commit()

    return {
        "claimed": len(snapshots),
        "checked": len(observations),
        "transitions": transitions,
    }
