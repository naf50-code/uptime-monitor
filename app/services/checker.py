import asyncio
import ipaddress
import random
import socket
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.db.models import CheckOutcome

MAX_CONCURRENT_CHECKS = 20
MAX_DUE_MONITORS_PER_RUN = 100
DNS_TIMEOUT_SECONDS = 2.0
class CheckTarget(Protocol):
    method: str
    url: str
    timeout_ms: int


@dataclass(frozen=True)
class CheckObservation:
    checked_at: datetime
    outcome: CheckOutcome
    latency_ms: int | None
    status_code: int | None
    error_detail: str | None
    retryable: bool = False


class UnsafeTargetError(Exception):
    """Raised when a monitor target resolves to a non-public address."""


async def _assert_public_destination(url: str) -> None:
    parsed = urlsplit(url)
    host = parsed.hostname
    if host is None:
        raise UnsafeTargetError
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise UnsafeTargetError
        return

    loop = asyncio.get_running_loop()
    try:
        addresses = await asyncio.wait_for(
            loop.getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=DNS_TIMEOUT_SECONDS,
        )
    except socket.gaierror as exc:
        raise exc
    if not addresses:
        raise socket.gaierror("No addresses returned")

    for address_info in addresses:
        address = ipaddress.ip_address(address_info[4][0])
        if not address.is_global:
            raise UnsafeTargetError


def _contains_tls_error(error: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (ssl.SSLError, ssl.CertificateError)):
            return True
        current = current.__cause__ or current.__context__
    return False


def _observation(
    outcome: CheckOutcome,
    latency_ms: int | None = None,
    status_code: int | None = None,
    error_detail: str | None = None,
    retryable: bool = False,
) -> CheckObservation:
    return CheckObservation(
        checked_at=datetime.now(UTC),
        outcome=outcome,
        latency_ms=latency_ms,
        status_code=status_code,
        error_detail=error_detail,
        retryable=retryable,
    )


async def _single_attempt(
    monitor: CheckTarget, client: httpx.AsyncClient
) -> CheckObservation:
    started = time.perf_counter()
    try:
        await _assert_public_destination(monitor.url)
        timeout = httpx.Timeout(monitor.timeout_ms / 1000)
        async with client.stream(
            monitor.method,
            monitor.url,
            timeout=timeout,
        ) as response:
            latency_ms = round((time.perf_counter() - started) * 1000)
            if 200 <= response.status_code < 400:
                return _observation(
                    CheckOutcome.SUCCESS,
                    latency_ms=latency_ms,
                    status_code=response.status_code,
                )
            return _observation(
                CheckOutcome.HTTP_ERROR,
                latency_ms=latency_ms,
                status_code=response.status_code,
                error_detail=f"Unexpected HTTP status {response.status_code}",
            )
    except UnsafeTargetError:
        return _observation(
            CheckOutcome.CONNECTION_ERROR,
            error_detail="Target resolves to a non-public address",
        )
    except (TimeoutError, httpx.TimeoutException):
        return _observation(
            CheckOutcome.TIMEOUT,
            error_detail="Request timed out",
            retryable=True,
        )
    except socket.gaierror:
        return _observation(
            CheckOutcome.DNS_ERROR,
            error_detail="DNS resolution failed",
            retryable=True,
        )
    except httpx.ConnectError as exc:
        if _contains_tls_error(exc):
            return _observation(
                CheckOutcome.TLS_ERROR,
                error_detail="TLS certificate validation failed",
            )
        return _observation(
            CheckOutcome.CONNECTION_ERROR,
            error_detail="Connection failed",
            retryable=True,
        )
    except httpx.RequestError:
        return _observation(
            CheckOutcome.CONNECTION_ERROR,
            error_detail="Network request failed",
            retryable=True,
        )
    except Exception:
        return _observation(
            CheckOutcome.INTERNAL_ERROR,
            error_detail="Unexpected checker error",
        )


async def check_monitor(
    monitor: CheckTarget, client: httpx.AsyncClient
) -> CheckObservation:
    for attempt in range(2):
        observation = await _single_attempt(monitor, client)
        if not observation.retryable or attempt == 1:
            return observation
        await asyncio.sleep(random.uniform(0.05, 0.2))
    return _observation(CheckOutcome.INTERNAL_ERROR, error_detail="Check did not run")


def make_http_client() -> httpx.AsyncClient:
    limits = httpx.Limits(
        max_connections=MAX_CONCURRENT_CHECKS,
        max_keepalive_connections=10,
    )
    return httpx.AsyncClient(
        limits=limits,
        follow_redirects=False,
        trust_env=False,
    )
