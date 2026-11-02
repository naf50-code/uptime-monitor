from fastapi import FastAPI

app = FastAPI(
    title="Uptime Monitor API",
    description="A portfolio project for monitoring API availability and latency.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
