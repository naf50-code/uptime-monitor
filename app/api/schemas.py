import ipaddress
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import CheckOutcome, MonitorState


def validate_target_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        # Accessing .port validates the port syntax and range.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("URL is malformed") from exc

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https")
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must have a host and cannot contain credentials")

    normalized_host = hostname.rstrip(".").lower()
    blocked_hosts = {
        "localhost",
        "metadata.google.internal",
        "metadata.google",
        "instance-data",
    }
    if (
        normalized_host in blocked_hosts
        or normalized_host.endswith(".localhost")
        or normalized_host.endswith(".local")
    ):
        raise ValueError("Local and metadata hosts cannot be monitored")

    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private and reserved IP addresses cannot be monitored")

    return value


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)
    method: str = Field(default="GET", pattern="^(GET|HEAD)$")
    interval_seconds: int = Field(default=300, ge=60, le=86400)
    timeout_ms: int = Field(default=5000, ge=500, le=15000)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @field_validator("url")
    @classmethod
    def url_must_be_safe(cls, value: str) -> str:
        return validate_target_url(value)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=8, max_length=2048)
    method: str | None = Field(default=None, pattern="^(GET|HEAD)$")
    interval_seconds: int | None = Field(default=None, ge=60, le=86400)
    timeout_ms: int | None = Field(default=None, ge=500, le=15000)
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @field_validator("url")
    @classmethod
    def url_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_target_url(value)


class MonitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    name: str
    url: str
    method: str
    interval_seconds: int
    timeout_ms: int
    enabled: bool
    consecutive_failures: int
    consecutive_successes: int
    current_state: MonitorState
    next_check_at: datetime
    created_at: datetime


class CheckResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: UUID
    checked_at: datetime
    latency_ms: int | None
    status_code: int | None
    outcome: CheckOutcome
    error_detail: str | None


class MonitorSummaryResponse(BaseModel):
    monitor_id: UUID
    window_hours: int
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    average_latency_ms: float | None
    p95_latency_ms: float | None
    last_checked_at: datetime | None
