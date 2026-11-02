from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account, get_db_session
from app.api.schemas import (
    CheckResultResponse,
    MonitorCreate,
    MonitorResponse,
    MonitorSummaryResponse,
    MonitorUpdate,
)
from app.db.models import Account, CheckOutcome, CheckResult, Monitor

router = APIRouter(prefix="/monitors", tags=["monitors"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentAccount = Annotated[Account, Depends(get_current_account)]


def visible_monitor_query(account: Account):
    query = select(Monitor)
    if account.role != "admin":
        query = query.where(Monitor.account_id == account.id)
    return query


async def get_visible_monitor(
    monitor_id: UUID, session: AsyncSession, account: Account
) -> Monitor:
    result = await session.execute(
        visible_monitor_query(account).where(Monitor.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()
    if monitor is None:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    payload: MonitorCreate, session: DbSession, account: CurrentAccount
) -> Monitor:
    monitor = Monitor(account_id=account.id, **payload.model_dump())
    session.add(monitor)
    await session.commit()
    await session.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorResponse])
async def list_monitors(
    session: DbSession,
    account: CurrentAccount,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Monitor]:
    result = await session.execute(
        visible_monitor_query(account)
        .order_by(Monitor.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: UUID, session: DbSession, account: CurrentAccount
) -> Monitor:
    return await get_visible_monitor(monitor_id, session, account)


@router.get("/{monitor_id}/results", response_model=list[CheckResultResponse])
async def list_monitor_results(
    monitor_id: UUID,
    session: DbSession,
    account: CurrentAccount,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CheckResult]:
    await get_visible_monitor(monitor_id, session, account)
    result = await session.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{monitor_id}/summary", response_model=MonitorSummaryResponse)
async def get_monitor_summary(
    monitor_id: UUID,
    session: DbSession,
    account: CurrentAccount,
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> MonitorSummaryResponse:
    """Summarize sampled check success and successful-response latency."""
    await get_visible_monitor(monitor_id, session, account)
    window_end = datetime.now(UTC)
    window_start = window_end - timedelta(hours=hours)
    filters = (
        CheckResult.monitor_id == monitor_id,
        CheckResult.checked_at >= window_start,
    )

    summary_result = await session.execute(
        select(
            func.count(CheckResult.id),
            func.count(CheckResult.id).filter(
                CheckResult.outcome == CheckOutcome.SUCCESS
            ),
            func.avg(CheckResult.latency_ms).filter(
                CheckResult.outcome == CheckOutcome.SUCCESS
            ),
            func.max(CheckResult.checked_at),
        ).where(*filters)
    )
    total_checks, successful_checks, average_latency, last_checked_at = (
        summary_result.one()
    )

    p95_result = await session.execute(
        select(func.percentile_cont(0.95).within_group(CheckResult.latency_ms)).where(
            *filters,
            CheckResult.outcome == CheckOutcome.SUCCESS,
            CheckResult.latency_ms.is_not(None),
        )
    )
    p95_latency = p95_result.scalar_one()
    uptime_percentage = (
        round(successful_checks * 100.0 / total_checks, 2) if total_checks else 0.0
    )

    return MonitorSummaryResponse(
        monitor_id=monitor_id,
        window_hours=hours,
        total_checks=total_checks,
        successful_checks=successful_checks,
        failed_checks=total_checks - successful_checks,
        uptime_percentage=uptime_percentage,
        average_latency_ms=(
            round(float(average_latency), 2) if average_latency is not None else None
        ),
        p95_latency_ms=round(float(p95_latency), 2) if p95_latency is not None else None,
        last_checked_at=last_checked_at,
    )


@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: UUID,
    payload: MonitorUpdate,
    session: DbSession,
    account: CurrentAccount,
) -> Monitor:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")

    monitor = await get_visible_monitor(monitor_id, session, account)
    for field, value in updates.items():
        setattr(monitor, field, value)
    if "interval_seconds" in updates:
        monitor.next_check_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(monitor)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: UUID, session: DbSession, account: CurrentAccount
) -> Response:
    monitor = await get_visible_monitor(monitor_id, session, account)
    await session.delete(monitor)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
