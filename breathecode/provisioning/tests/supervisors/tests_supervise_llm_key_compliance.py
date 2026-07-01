from unittest.mock import MagicMock, patch

from breathecode.provisioning.supervisors import supervise_llm_key_compliance


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
    models=None,
    team_spend=0.0,
    team_max_budget=5.0,
    team_budget_duration="30d",
    team_member_budget_id="budget-1",
    member_max_budget=5.0,
    member_budget_duration="30d",
):
    return {
        "team_id": team_id,
        "member_user_ids": frozenset(),
        "academy_config": academy_config,
        "models": models if models is not None else ["miami/gpt-4"],
        "team_spend": team_spend,
        "team_max_budget": team_max_budget,
        "team_budget_duration": team_budget_duration,
        "team_member_budget_id": team_member_budget_id,
        "member_max_budget": member_max_budget,
        "member_budget_duration": member_budget_duration,
    }


def _issues_from_supervisor():
    return list(supervise_llm_key_compliance.__wrapped__())


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_groups_multiple_key_alerts_into_one_issue(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "keys": [
            {
                "token_id": "tok-broken",
                "key_alias": "test_alias",
                "user_id": None,
                "team_id": None,
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
        ],
    }

    issues = _issues_from_supervisor()
    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]

    assert len(alert_issues) == 1
    assert alert_issues[0][2]["token_id"] == "tok-broken"
    assert alert_issues[0][2]["issue_count"] == 2
    message = alert_issues[0][2]["message"]
    assert message == alert_issues[0][0]
    assert 'LiteLLM compliance alert — key "test_alias" (2 issues)' in message
    assert "has no team_id" in message
    assert "has no user_id" in message
    assert "tok-broken" not in message


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_returns_no_issues_for_empty_snapshot(collect_mock):
    collect_mock.return_value = _empty_snapshot()

    assert _issues_from_supervisor() == []
    collect_mock.assert_called_once()


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_key_issues(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "keys": [
            {
                "token_id": "tok-no-team",
                "key_alias": "student-key-no-team",
                "user_id": "student-miami",
                "team_id": None,
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": None,
            },
            {
                "token_id": "tok-no-expires",
                "key_alias": None,
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": None,
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
            {
                "token_id": "tok-no-user",
                "key_alias": None,
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
        ],
        "academies": [academy_config],
    }

    issues = _issues_from_supervisor()
    codes = {issue[1] for issue in issues}

    assert codes == {
        "fix-llm-key-missing-expires",
        "alert-llm-compliance",
    }

    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]
    assert len(alert_issues) == 2

    team_id_issue = next(issue for issue in alert_issues if issue[2]["token_id"] == "tok-no-team")
    assert team_id_issue[2]["grouped"] is True
    assert team_id_issue[2]["message"] == "LiteLLM key student-key-no-team has no team_id"
    assert team_id_issue[0] == team_id_issue[2]["message"]
    assert "academy_config" not in team_id_issue[2]

    expires_issue = next(issue for issue in issues if issue[1] == "fix-llm-key-missing-expires")
    assert expires_issue[2] == {
        "token_id": "tok-no-expires",
        "team_id": "team-1",
        "provisioning_academy_id": 1,
    }

    missing_user_issue = next(issue for issue in alert_issues if issue[2]["token_id"] == "tok-no-user")
    assert missing_user_issue[2]["token_id"] == "tok-no-user"
    assert "has no user_id" in missing_user_issue[2]["message"]
    assert missing_user_issue[2]["academy_config"] == academy_config


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_too_many_keys_per_user(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "keys": [
            {
                "token_id": f"tok-{index}",
                "key_alias": None,
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
            }
            for index in range(7)
        ],
    }

    issues = _issues_from_supervisor()

    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-compliance"
    assert issues[0][2]["grouped"] is True
    assert issues[0][2]["user_id"] == "student-miami"
    assert "has 7 keys (>= 7)" in issues[0][2]["message"]
    assert issues[0][2]["academy_config"] == academy_config


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_external_user_issues(collect_mock):
    provisioning_llm = MagicMock()
    academy_config = _make_academy_config(academy_slug="miami", team_id="team-1")

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "llm_external_users": [
            {
                "user_id": "intruder",
                "user_role": "internal_user_viewer",
                "teams": [],
                "key_count": 0,
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
            {
                "user_id": "student-miami",
                "user_role": "internal_user_viewer",
                "teams": [],
                "key_count": 1,
                "provisioning_llm": provisioning_llm,
                "academy_config": academy_config,
            },
            {
                "user_id": "default_user_id",
                "user_role": "proxy_admin",
                "teams": [],
                "key_count": 3,
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
        ],
    }

    issues = _issues_from_supervisor()
    codes = {issue[1] for issue in issues}

    assert codes == {
        "alert-llm-compliance",
        "fix-llm-user-missing-team",
    }

    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]
    assert len(alert_issues) == 1

    missing_team_issue = next(issue for issue in issues if issue[1] == "fix-llm-user-missing-team")
    assert missing_team_issue[2] == {
        "user_id": "student-miami",
        "team_id": "team-1",
        "provisioning_academy_id": 1,
    }

    intruder_issue = alert_issues[0]
    assert intruder_issue[2]["user_id"] == "intruder"
    assert intruder_issue[2]["issue_count"] == 2
    assert "has no active ProvisioningLLM record" in intruder_issue[2]["message"]
    assert "does not follow the username-academy_slug convention" in intruder_issue[2]["message"]
    assert intruder_issue[2]["academy_config"] == academy_config


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_yields_alert_without_recipients(collect_mock):
    academy_config = _make_academy_config(alert_emails=[])

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "keys": [
            {
                "token_id": "tok-no-user",
                "key_alias": None,
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": academy_config,
            },
        ],
    }

    issues = _issues_from_supervisor()

    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-compliance"
    assert "has no user_id" in issues[0][2]["message"]
    assert issues[0][2]["academy_config"] == academy_config
    assert issues[0][2]["academy_config"]["alert_emails"] == []


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_yields_alert_without_academy_config(collect_mock):
    collect_mock.return_value = {
        **_empty_snapshot(),
        "keys": [
            {
                "token_id": "tok-no-user",
                "key_alias": None,
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_llm": None,
                "academy_config": None,
            },
        ],
    }

    issues = _issues_from_supervisor()

    assert len(issues) == 1
    assert issues[0][1] == "alert-llm-compliance"
    assert issues[0][2]["token_id"] == "tok-no-user"
    assert "has no user_id" in issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_skips_excluded_external_users(collect_mock):
    collect_mock.return_value = {
        **_empty_snapshot(),
        "llm_external_users": [
            {
                "user_id": "default_user_id",
                "user_role": "proxy_admin",
                "teams": [],
                "key_count": 3,
                "provisioning_llm": None,
                "academy_config": _make_academy_config(),
            }
        ],
    }

    assert _issues_from_supervisor() == []


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_team_config_issues(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "teams": [
            _make_team_row(
                academy_config=academy_config,
                models=["miami/gpt-4", "openai/gpt-4"],
                team_spend=4.6,
                team_max_budget=5.0,
                team_budget_duration=None,
                team_member_budget_id=None,
                member_max_budget=None,
                member_budget_duration=None,
            ),
            _make_team_row(
                team_id="team-orphan",
                academy_config=None,
                models=["openai/gpt-4"],
                team_budget_duration=None,
            ),
        ],
    }

    issues = _issues_from_supervisor()
    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]

    assert len(alert_issues) == 1
    assert alert_issues[0][2]["team_id"] == "team-1"
    assert alert_issues[0][2]["issue_count"] == 3

    message = alert_issues[0][2]["message"]
    assert "models without miami/ prefix" in message and "openai/gpt-4" in message
    assert "budget fields not defined" in message
    assert "team budget_duration" in message
    assert "team_member_budget_id" in message
    assert "team max_budget" not in message.split("budget fields not defined", 1)[1]
    assert "spend is 92% of max_budget" in message
    assert alert_issues[0][2]["academy_config"] == academy_config


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_missing_member_budget_duration(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "teams": [
            _make_team_row(
                academy_config=academy_config,
                team_spend=0.0,
                member_budget_duration=None,
            ),
        ],
    }

    issues = _issues_from_supervisor()
    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]

    assert len(alert_issues) == 1
    assert "budget fields not defined" in alert_issues[0][2]["message"]
    assert "member budget_duration" in alert_issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_missing_team_max_budget(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "teams": [
            _make_team_row(
                academy_config=academy_config,
                team_spend=0.0,
                team_max_budget=0.0,
            ),
        ],
    }

    issues = _issues_from_supervisor()
    alert_issues = [issue for issue in issues if issue[1] == "alert-llm-compliance"]

    assert len(alert_issues) == 1
    assert "budget fields not defined" in alert_issues[0][2]["message"]
    assert "team max_budget" in alert_issues[0][2]["message"]


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_skips_team_config_for_healthy_team(collect_mock):
    academy_config = _make_academy_config()

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy_config],
        "teams": [
            _make_team_row(
                academy_config=academy_config,
                team_spend=1.0,
                team_budget_duration="24h",
                member_budget_duration="24h",
            )
        ],
    }

    assert _issues_from_supervisor() == []
