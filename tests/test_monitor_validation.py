import pytest
from pydantic import ValidationError

from app.api.schemas import MonitorCreate


def test_accepts_public_http_monitor_target() -> None:
    monitor = MonitorCreate(name="  Example  ", url="https://example.com/")

    assert monitor.name == "Example"
    assert monitor.method == "GET"
    assert monitor.interval_seconds == 300


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/",
        "https://user:password@example.com/",
    ],
)
def test_rejects_unsafe_monitor_targets(url: str) -> None:
    with pytest.raises(ValidationError):
        MonitorCreate(name="Unsafe target", url=url)
