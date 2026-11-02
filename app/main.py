import logging

from fastapi import FastAPI
from fastapi import HTTPException
from sqlalchemy import text

from app.api.routes.auth import router as auth_router
from app.api.routes.internal import router as internal_router
from app.api.routes.monitors import router as monitors_router
from app.db.session import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Uptime Monitor API",
    description="A portfolio project for monitoring API availability and latency.",
    version="0.1.0",
)
app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(monitors_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/health/database", tags=["health"])
async def database_health_check() -> dict[str, str]:
    """Check that PostgreSQL accepts a simple query."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "reachable"}
