from datetime import datetime

from breathecode.assignments.utils.indicators import EngagementIndicator, FrustrationIndicator, UserIndicatorCalculator

INDICATORS = [EngagementIndicator(), FrustrationIndicator()]

# 2024-01-15T10:00:00 UTC in milliseconds
OPENED_AT_MS = 1705312800000
# 2024-01-15T11:30:00 UTC in milliseconds
COMPLETED_AT_MS = 1705318200000


def _base_telemetry(steps, **overrides):
    data = {
        "last_interaction_at": COMPLETED_AT_MS,
        "tutorial_started_at": OPENED_AT_MS,
        "workout_session": [{}],
        "steps": steps,
    }
    data.update(overrides)
    return data


def test_step_with_null_completed_at_does_not_crash():
    telemetry = _base_telemetry(
        [
            {
                "slug": "step-1",
                "opened_at": OPENED_AT_MS,
                "completed_at": None,
            }
        ]
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    metrics = calculator.calculate_step_metrics(telemetry["steps"][0])

    assert metrics["status"] == "skipped"
    assert metrics["time_spent"] > 0


def test_step_with_iso_completed_at_is_marked_completed():
    telemetry = _base_telemetry(
        [
            {
                "slug": "step-1",
                "opened_at": OPENED_AT_MS,
                "completed_at": "2024-01-15T11:30:00Z",
            }
        ]
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    metrics = calculator.calculate_step_metrics(telemetry["steps"][0])

    assert metrics["status"] == "completed"
    assert metrics["time_spent"] == 5400.0


def test_step_with_epoch_completed_at_still_works():
    telemetry = _base_telemetry(
        [
            {
                "slug": "step-1",
                "opened_at": OPENED_AT_MS,
                "completed_at": COMPLETED_AT_MS,
            }
        ]
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    metrics = calculator.calculate_step_metrics(telemetry["steps"][0])

    assert metrics["status"] == "completed"
    assert metrics["time_spent"] == 5400.0


def test_global_metrics_with_missing_tutorial_started_at_defaults_to_zero():
    telemetry = _base_telemetry(
        [{"slug": "step-1", "opened_at": OPENED_AT_MS, "completed_at": COMPLETED_AT_MS}],
        tutorial_started_at=None,
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    global_metrics = calculator.calculate_global_metrics()

    assert global_metrics["total_time_on_platform"] == 0


def test_global_metrics_with_missing_last_interaction_at_defaults_to_zero():
    telemetry = _base_telemetry(
        [{"slug": "step-1", "opened_at": OPENED_AT_MS, "completed_at": COMPLETED_AT_MS}],
        last_interaction_at=None,
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    global_metrics = calculator.calculate_global_metrics()

    assert global_metrics["total_time_on_platform"] == 0


def test_calculate_indicators_with_null_completed_at_does_not_crash():
    telemetry = _base_telemetry(
        [
            {
                "slug": "step-1",
                "opened_at": OPENED_AT_MS,
                "completed_at": None,
            }
        ]
    )

    calculator = UserIndicatorCalculator(telemetry, INDICATORS)
    results = calculator.calculate_indicators()

    assert results["steps"][0]["metrics"]["status"] == "skipped"
    assert "global" in results


def test_parse_timestamp_accepts_datetime_instance():
    telemetry = _base_telemetry([])
    calculator = UserIndicatorCalculator(telemetry, INDICATORS)

    dt = datetime(2024, 1, 15, 11, 30, 0)
    assert calculator.parse_timestamp(dt) == dt
