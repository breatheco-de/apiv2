from unittest.mock import MagicMock, patch

from breathecode.provisioning.supervisors import (
    alert_llm_compliance,
    fix_llm_key_missing_expires,
    fix_llm_user_missing_team,
)
from breathecode.provisioning.utils.llm_client import LLMClientError


def _run_issue_handler(handler, **params):
    issue = MagicMock()
    issue.params = params
    issue.fixed = None

    with patch("breathecode.monitoring.models.SupervisorIssue.objects.filter") as filter_mock:
        filter_mock.return_value.first.return_value = issue
        return handler(1)


@patch("breathecode.provisioning.supervisors.get_llm_client")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_fix_llm_key_missing_expires_updates_key(provisioning_academy_objects_mock, get_llm_client_mock):
    provisioning_academy = MagicMock()
    provisioning_academy_objects_mock.filter.return_value.first.return_value = provisioning_academy

    client_mock = MagicMock()
    get_llm_client_mock.return_value = client_mock

    result = _run_issue_handler(
        fix_llm_key_missing_expires,
        token_id="tok-1",
        team_id="team-1",
        provisioning_academy_id=1,
    )

    assert result is True
    client_mock.update_key.assert_called_once_with(key="tok-1", duration="30d")


@patch("breathecode.provisioning.supervisors.get_llm_client")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_fix_llm_key_missing_expires_retries_on_client_error(provisioning_academy_objects_mock, get_llm_client_mock):
    provisioning_academy = MagicMock()
    provisioning_academy_objects_mock.filter.return_value.first.return_value = provisioning_academy

    client_mock = MagicMock()
    client_mock.update_key.side_effect = LLMClientError("temporary failure")
    get_llm_client_mock.return_value = client_mock

    result = _run_issue_handler(
        fix_llm_key_missing_expires,
        token_id="tok-1",
        team_id="team-1",
        provisioning_academy_id=1,
    )

    assert result is None


@patch("breathecode.provisioning.supervisors.get_llm_client")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_fix_llm_user_missing_team_adds_user(provisioning_academy_objects_mock, get_llm_client_mock):
    provisioning_academy = MagicMock()
    provisioning_academy_objects_mock.filter.return_value.first.return_value = provisioning_academy

    client_mock = MagicMock()
    get_llm_client_mock.return_value = client_mock

    result = _run_issue_handler(
        fix_llm_user_missing_team,
        user_id="student-miami",
        team_id="team-1",
        provisioning_academy_id=1,
    )

    assert result is True
    client_mock.add_user_to_team.assert_called_once_with(team_id="team-1", user_ids=["student-miami"])


@patch("breathecode.provisioning.supervisors.get_llm_client")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_fix_llm_user_missing_team_treats_duplicate_as_fixed(provisioning_academy_objects_mock, get_llm_client_mock):
    provisioning_academy = MagicMock()
    provisioning_academy_objects_mock.filter.return_value.first.return_value = provisioning_academy

    client_mock = MagicMock()
    client_mock.add_user_to_team.side_effect = LLMClientError("409 already exists")
    get_llm_client_mock.return_value = client_mock

    result = _run_issue_handler(
        fix_llm_user_missing_team,
        user_id="student-miami",
        team_id="team-1",
        provisioning_academy_id=1,
    )

    assert result is True


@patch("breathecode.provisioning.supervisors.send_email_message")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_alert_llm_compliance_sends_diagnostic_email(provisioning_academy_objects_mock, send_email_mock):
    provisioning_academy = MagicMock()
    provisioning_academy.academy = MagicMock()
    provisioning_academy_objects_mock.filter.return_value.select_related.return_value.first.return_value = (
        provisioning_academy
    )

    message = "LiteLLM user student-miami has 7 keys (>= 7)"
    result = _run_issue_handler(
        alert_llm_compliance,
        message=message,
        academy_config={
            "provisioning_academy_id": 1,
            "academy_slug": "miami",
            "team_id": "team-1",
            "alert_emails": ["ops@example.com"],
        },
    )

    assert result is True
    send_email_mock.assert_called_once_with(
        "diagnostic",
        ["ops@example.com"],
        {
            "subject": f"LiteLLM compliance alert: {message}",
            "details": message,
        },
        academy=provisioning_academy.academy,
    )


@patch("breathecode.provisioning.supervisors.send_email_message")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_alert_llm_compliance_skips_email_without_recipients(provisioning_academy_objects_mock, send_email_mock):
    result = _run_issue_handler(
        alert_llm_compliance,
        message="LiteLLM key tok-1 has no user_id",
        academy_config={
            "provisioning_academy_id": 1,
            "academy_slug": "miami",
            "team_id": "team-1",
            "alert_emails": [],
        },
    )

    assert result is True
    send_email_mock.assert_not_called()


@patch("breathecode.provisioning.supervisors.send_email_message")
@patch("breathecode.provisioning.supervisors.ProvisioningAcademy.objects")
def test_alert_llm_compliance_skips_email_without_provisioning_academy(
    provisioning_academy_objects_mock, send_email_mock
):
    provisioning_academy_objects_mock.filter.return_value.select_related.return_value.first.return_value = None

    result = _run_issue_handler(
        alert_llm_compliance,
        message="LiteLLM key tok-1 has no user_id",
        academy_config={
            "provisioning_academy_id": 1,
            "academy_slug": "miami",
            "team_id": "team-1",
            "alert_emails": ["ops@example.com"],
        },
    )

    assert result is True
    send_email_mock.assert_not_called()
