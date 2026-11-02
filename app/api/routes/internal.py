import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.scheduler import run_due_checks

router = APIRouter(prefix="/internal", tags=["internal scheduler"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/run-due-checks")
async def trigger_due_checks(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    force: bool = Query(default=False),
) -> dict[str, int]:
    expected_token = os.getenv("SCHEDULER_TOKEN", "")
    if len(expected_token.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not configured",
        )
    if credentials is None or not hmac.compare_digest(
        credentials.credentials, expected_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid scheduler token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await run_due_checks(force=force)
