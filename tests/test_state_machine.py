from app.db.models import MonitorState
from app.services.state_machine import apply_observation


def test_three_consecutive_failures_mark_monitor_down() -> None:
    state = MonitorState.UNKNOWN
    failures = 0
    successes = 0

    for _ in range(3):
        state, failures, successes = apply_observation(
            state, failures, successes, succeeded=False
        )

    assert state == MonitorState.DOWN
    assert failures == 3
    assert successes == 0


def test_recovery_requires_two_successes_after_down() -> None:
    state, failures, successes = apply_observation(
        MonitorState.DOWN, 3, 0, succeeded=True
    )
    assert state == MonitorState.DOWN
    assert failures == 0
    assert successes == 1

    state, failures, successes = apply_observation(
        state, failures, successes, succeeded=True
    )
    assert state == MonitorState.UP
    assert successes == 2
