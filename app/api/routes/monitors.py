from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account, get_db_session
from app.api.schemas import MonitorCreate, MonitorResponse, MonitorUpdate
from app.db.models import Account, Monitor

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
