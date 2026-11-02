from app.db.models import MonitorState

FAILURES_BEFORE_DOWN = 3
SUCCESSES_BEFORE_RECOVERY = 2


def apply_observation(
    current_state: MonitorState,
    consecutive_failures: int,
    consecutive_successes: int,
    succeeded: bool,
) -> tuple[MonitorState, int, int]:
    if succeeded:
        consecutive_failures = 0
        consecutive_successes += 1
        if current_state == MonitorState.DOWN:
            next_state = (
                MonitorState.UP
                if consecutive_successes >= SUCCESSES_BEFORE_RECOVERY
                else MonitorState.DOWN
            )
        else:
            next_state = MonitorState.UP
    else:
        consecutive_successes = 0
        consecutive_failures += 1
        next_state = (
            MonitorState.DOWN
            if consecutive_failures >= FAILURES_BEFORE_DOWN
            else MonitorState.DEGRADED
        )

    return next_state, consecutive_failures, consecutive_successes
