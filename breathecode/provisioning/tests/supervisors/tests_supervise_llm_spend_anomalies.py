from unittest.mock import patch

from breathecode.provisioning.supervisors import supervise_llm_spend_anomalies


def _empty_snapshot():
    return {
        "keys": [],
        "teams": [],
        "academies": [],
        "provisioning_users": [],
        "llm_external_users": [],
    }


def _make_academy_config(*, pa_id=1, academy_slug="miami", team_id="team-1", alert_emails=None):
    emails = ["ops@example.com"] if alert_emails is None else alert_emails

    return {
        "provisioning_academy_id": pa_id,
        "academy_slug": academy_slug,
        "team_id": team_id,
        "alert_emails": emails,
    }


def _make_team_row(
    *,
    team_id="team-1",
    academy_config=None,
    team_max_budget=5.0,
    member_max_budget=1.0,
    team_daily_spend=0.0,
):
    return {
        "team_id": team_id,
        "member_user_ids": frozenset(),
        "academy_config": academy_config,
        "models": ["miami/gpt-4"],
        "team_spend": 0.0,
        "team_max_budget": team_max_budget,
        "team_budget_duration": "30d",
        "team_member_budget_id": "budget-1",
        "member_max_budget": member_max_budget,
        "member_budget_duration": "30d",
        "team_daily_spend": team_daily_spend,
    }


def _issues_from_supervisor():
    return list(supervise_llm_spend_anomalies.__wrapped__())


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_returns_no_issues_for_empty_snapshot(collect_mock):
    collect_mock.return_value = _empty_snapshot()

    assert _issues_from_supervisor() == []


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_detects_team_daily_spend_near_limit(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "teams": [
            _make_team_row(
                academy_config=academy_config,
                team_max_budget=5.0,
                team_daily_spend=4.6,
            )
        ],
    }

    issues = _issues_from_supervisor()
    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-spend-anomaly"
    assert "has high single-day spend: 92% of max_budget" in issues[0][2]["message"]
    assert "for today only" in issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_detects_user_daily_spend_near_limit(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "teams": [
            _make_team_row(
                team_id="team-1",
                academy_config=academy_config,
                member_max_budget=1.0,
            )
        ],
        "llm_external_users": [
            {
                "user_id": "student-miami",
                "user_role": "internal_user_viewer",
                "teams": ["team-1"],
                "key_count": 1,
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 0.95,
            }
        ],
    }

    issues = _issues_from_supervisor()
    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-spend-anomaly"
    assert "has high single-day spend: 95% of member max_budget" in issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_detects_user_daily_spend_with_fallback_budget(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "llm_external_users": [
            {
                "user_id": "orphan-user",
                "user_role": "internal_user_viewer",
                "teams": [],
                "key_count": 1,
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 9.5,
            }
        ],
    }

    issues = _issues_from_supervisor()
    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-spend-anomaly"
    assert "has high single-day spend: 95% of fallback max_budget (10.0 USD)" in issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_detects_key_without_user_daily_spend_near_limit(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "teams": [
            _make_team_row(
                team_id="team-1",
                academy_config=academy_config,
                member_max_budget=1.0,
            )
        ],
        "keys": [
            {
                "token_id": "tok-no-user",
                "key_alias": "orphan-key",
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-12-31T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 0.95,
            }
        ],
    }

    issues = _issues_from_supervisor()
    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-spend-anomaly"
    assert "orphan-key" in issues[0][2]["message"]
    assert "no user_id" in issues[0][2]["message"]
    assert "95% of member max_budget" in issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_skips_key_without_user_below_threshold(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "teams": [
            _make_team_row(
                team_id="team-1",
                academy_config=academy_config,
                member_max_budget=1.0,
            )
        ],
        "keys": [
            {
                "token_id": "tok-no-user",
                "key_alias": "orphan-key",
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-12-31T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 0.5,
            }
        ],
    }

    assert _issues_from_supervisor() == []


@patch("breathecode.provisioning.supervisors.collect_llm_daily_spend")
def test_supervise_llm_spend_anomalies_skips_key_with_user_for_key_level_check(collect_mock):
    academy_config = _make_academy_config()
    collect_mock.return_value = {
        **_empty_snapshot(),
        "teams": [
            _make_team_row(
                team_id="team-1",
                academy_config=academy_config,
                member_max_budget=1.0,
            )
        ],
        "keys": [
            {
                "token_id": "tok-with-user",
                "key_alias": "user-key",
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": "2026-12-31T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 0.95,
            }
        ],
        "llm_external_users": [
            {
                "user_id": "student-miami",
                "user_role": "internal_user_viewer",
                "teams": ["team-1"],
                "key_count": 1,
                "provisioning_llm": None,
                "academy_config": academy_config,
                "daily_spend": 0.95,
            }
        ],
    }

    issues = _issues_from_supervisor()
    assert len(issues) == 1
    assert "user-key" not in issues[0][2]["message"]
    assert "student-miami" in issues[0][2]["message"]
