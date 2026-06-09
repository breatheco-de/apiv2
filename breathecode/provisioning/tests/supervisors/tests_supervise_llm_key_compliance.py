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


def _make_academy_config(*, pa_id=1, academy_slug="miami", team_id="team-1"):
    academy = MagicMock()
    academy.slug = academy_slug

    provisioning_academy = MagicMock()
    provisioning_academy.id = pa_id
    provisioning_academy.academy = academy

    return {
        "provisioning_academy": provisioning_academy,
        "team_id": team_id,
    }


def _issues_from_supervisor():
    return list(supervise_llm_key_compliance.__wrapped__())


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_returns_no_issues_for_empty_snapshot(collect_mock):
    collect_mock.return_value = _empty_snapshot()

    assert _issues_from_supervisor() == []
    collect_mock.assert_called_once()


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_key_issues(collect_mock):
    collect_mock.return_value = {
        **_empty_snapshot(),
        "keys": [
            {
                "token_id": "tok-no-team",
                "key_alias": "student-key-no-team",
                "user_id": "student-miami",
                "team_id": None,
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_academy": None,
                "provisioning_llm": None,
            },
            {
                "token_id": "tok-no-expires",
                "key_alias": None,
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": None,
                "provisioning_academy": None,
                "provisioning_llm": None,
            },
            {
                "token_id": "tok-no-user",
                "key_alias": None,
                "user_id": None,
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_academy": None,
                "provisioning_llm": None,
            },
        ],
    }

    issues = _issues_from_supervisor()
    codes = {issue[1] for issue in issues}

    assert codes == {
        "llm-key-missing-team-id",
        "llm-key-missing-expires",
        "llm-key-missing-user-id",
    }

    team_id_issue = next(issue for issue in issues if issue[1] == "llm-key-missing-team-id")
    assert "student-key-no-team" in team_id_issue[0]
    assert "tok-no-team" not in team_id_issue[0]


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_too_many_keys_per_user(collect_mock):
    collect_mock.return_value = {
        **_empty_snapshot(),
        "keys": [
            {
                "token_id": f"tok-{index}",
                "key_alias": None,
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": "2026-01-01T00:00:00Z",
                "provisioning_academy": None,
                "provisioning_llm": None,
            }
            for index in range(7)
        ],
    }

    issues = _issues_from_supervisor()

    assert len(issues) == 1
    assert issues[0][1] == "llm-user-too-many-keys"
    assert issues[0][2] == {"user_id": "student-miami", "key_count": 7}


@patch("breathecode.provisioning.supervisors.collect_llm_data")
def test_supervise_llm_key_compliance_detects_external_user_issues(collect_mock):
    provisioning_llm = MagicMock()
    academy = _make_academy_config(academy_slug="miami", team_id="team-1")

    collect_mock.return_value = {
        **_empty_snapshot(),
        "academies": [academy],
        "llm_external_users": [
            {
                "user_id": "intruder",
                "user_role": "internal_user_viewer",
                "teams": [],
                "key_count": 0,
                "provisioning_academy": None,
                "provisioning_llm": None,
            },
            {
                "user_id": "student-miami",
                "user_role": "internal_user_viewer",
                "teams": [],
                "key_count": 1,
                "provisioning_academy": academy["provisioning_academy"],
                "provisioning_llm": provisioning_llm,
            },
            {
                "user_id": "default_user_id",
                "user_role": "proxy_admin",
                "teams": [],
                "key_count": 3,
                "provisioning_academy": None,
                "provisioning_llm": None,
            },
        ],
    }

    issues = _issues_from_supervisor()
    codes = {issue[1] for issue in issues}

    assert codes == {
        "llm-external-user-without-provisioning",
        "llm-external-user-invalid-convention",
        "llm-user-missing-team",
    }

    missing_team_issue = next(issue for issue in issues if issue[1] == "llm-user-missing-team")
    assert missing_team_issue[2] == {
        "user_id": "student-miami",
        "team_id": "team-1",
        "provisioning_academy_id": academy["provisioning_academy"].id,
    }


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
                "provisioning_academy": None,
                "provisioning_llm": None,
            }
        ],
    }

    assert _issues_from_supervisor() == []
