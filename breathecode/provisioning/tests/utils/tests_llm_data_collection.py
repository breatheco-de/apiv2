from unittest.mock import MagicMock, patch

from breathecode.provisioning.models import ProvisioningAcademy, ProvisioningLLM
from breathecode.provisioning.utils.llm_data_collection import collect_llm_data


def _make_provisioning_academy_mock(
    *,
    pa_id=1,
    academy_id=1,
    academy_slug="miami",
    vendor_id=10,
    team_id="team-1",
    api_url="https://litellm.example.com",
    credentials_token="master-key",
):
    academy = MagicMock()
    academy.id = academy_id
    academy.slug = academy_slug

    vendor = MagicMock()
    vendor.id = vendor_id
    vendor.api_url = api_url

    pa = MagicMock(spec=ProvisioningAcademy)
    pa.id = pa_id
    pa.academy = academy
    pa.academy_id = academy_id
    pa.vendor = vendor
    pa.vendor_id = vendor_id
    pa.credentials_token = credentials_token
    pa.credentials_key = ""
    pa.vendor_settings = {"team_id": team_id}
    return pa


def _make_provisioning_llm_mock(*, external_user_id="student-miami", academy_id=1, vendor_id=10):
    provisioning_llm = MagicMock(spec=ProvisioningLLM)
    provisioning_llm.external_user_id = external_user_id
    provisioning_llm.academy_id = academy_id
    provisioning_llm.vendor_id = vendor_id
    provisioning_llm.status = ProvisioningLLM.STATUS_ACTIVE
    return provisioning_llm


def _patch_provisioning_academy_query(provisioning_academy_objects_mock, provisioning_academies):
    filter_mock = MagicMock()
    # list(queryset) is used instead of .iterator()
    filter_mock.__iter__.return_value = iter(provisioning_academies)
    provisioning_academy_objects_mock.select_related.return_value.filter.return_value = filter_mock
    return filter_mock


def _patch_active_provisioning_llms(provisioning_llm_objects_mock, provisioning_llms):
    active_qs = MagicMock()
    active_qs.exclude.return_value.exclude.return_value = active_qs
    active_qs.__iter__.return_value = iter(provisioning_llms)
    provisioning_llm_objects_mock.filter.return_value = active_qs
    return active_qs


def _list_keys_page(keys, page=1, total_pages=1):
    return {"keys": keys, "page": page, "total_pages": total_pages}


def _list_users_page(users, page=1, total_pages=1):
    return {"users": users, "page": page, "total_pages": total_pages}


@patch("breathecode.provisioning.utils.llm_data_collection.get_llm_client")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningLLM.objects")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningAcademy.objects")
def test_collect_llm_data_builds_flat_enriched_rows(
    provisioning_academy_objects_mock,
    provisioning_llm_objects_mock,
    get_llm_client_mock,
):
    pa = _make_provisioning_academy_mock()
    provisioning_llm = _make_provisioning_llm_mock()
    _patch_provisioning_academy_query(provisioning_academy_objects_mock, [pa])
    _patch_active_provisioning_llms(provisioning_llm_objects_mock, [provisioning_llm])

    client_mock = MagicMock()
    client_mock.list_keys.return_value = _list_keys_page(
        [
            {
                "token_id": "tok-1",
                "key_alias": "student-key",
                "user_id": "student-miami",
                "team_id": "team-1",
                "expires": "2026-01-31T00:00:00Z",
            },
            {
                "token_id": "tok-orphan",
                "key_alias": "orphan",
                "user_id": None,
                "team_id": None,
            },
        ]
    )
    client_mock.list_users.return_value = _list_users_page(
        [
            {
                "user_id": "student-miami",
                "user_role": "internal_user_viewer",
                "teams": ["team-1"],
                "key_count": 1,
            },
            {
                "user_id": "intruder-miami",
                "user_role": "internal_user_viewer",
                "teams": ["team-1", "team-other"],
                "key_count": 0,
            },
            {
                "user_id": "default_user_id",
                "user_role": "proxy_admin",
                "teams": ["team-1"],
                "key_count": 3,
            },
        ]
    )
    client_mock.list_teams.return_value = {
        "teams": [
            {
                "team_id": "team-1",
                "members_with_roles": [{"user_id": "student-miami", "role": "user"}],
                "models": ["miami/gpt-4", "groq/llama-3.1-8b-instant"],
                "spend": 1.25,
                "max_budget": 5.0,
                "budget_duration": "30d",
                "metadata": {
                    "soft_budget_alerting_emails": ["ops@example.com", "lead@example.com"],
                    "team_member_budget_id": "budget-1",
                },
            }
        ]
    }
    client_mock.get_budgets_info.return_value = [{"budget_id": "budget-1", "max_budget": 7.0, "budget_duration": "30d"}]
    get_llm_client_mock.return_value = client_mock

    snapshot = collect_llm_data()

    assert len(snapshot["keys"]) == 2
    assert len(snapshot["teams"]) == 1
    assert len(snapshot["academies"]) == 1
    assert len(snapshot["provisioning_users"]) == 1
    assert len(snapshot["llm_external_users"]) == 3

    student_key = next(key for key in snapshot["keys"] if key["token_id"] == "tok-1")
    assert student_key["user_id"] == "student-miami"
    assert student_key["team_id"] == "team-1"
    assert student_key["provisioning_llm"] is provisioning_llm

    orphan_key = next(key for key in snapshot["keys"] if key["token_id"] == "tok-orphan")
    assert orphan_key["team_id"] is None
    assert orphan_key["provisioning_llm"] is None

    assert snapshot["teams"][0]["team_id"] == "team-1"
    assert snapshot["teams"][0]["member_user_ids"] == frozenset({"student-miami"})
    assert snapshot["teams"][0]["academy_config"] is snapshot["academies"][0]
    assert snapshot["teams"][0]["models"] == ["miami/gpt-4", "groq/llama-3.1-8b-instant"]
    assert snapshot["teams"][0]["team_spend"] == 1.25
    assert snapshot["teams"][0]["team_max_budget"] == 5.0
    assert snapshot["teams"][0]["team_budget_duration"] == "30d"
    assert snapshot["teams"][0]["team_member_budget_id"] == "budget-1"
    assert snapshot["teams"][0]["member_max_budget"] == 7.0
    assert snapshot["teams"][0]["member_budget_duration"] == "30d"
    client_mock.get_budgets_info.assert_called_once_with(budgets=["budget-1"])

    assert snapshot["academies"][0]["team_id"] == "team-1"
    assert snapshot["academies"][0]["provisioning_academy_id"] == pa.id
    assert snapshot["academies"][0]["academy_slug"] == "miami"
    assert snapshot["academies"][0]["alert_emails"] == ["ops@example.com", "lead@example.com"]

    assert student_key["academy_config"] is snapshot["academies"][0]
    assert orphan_key["academy_config"] is snapshot["academies"][0]

    assert snapshot["provisioning_users"][0]["provisioning_academy"] is pa
    assert snapshot["provisioning_users"][0]["provisioning_llm"] is provisioning_llm

    student_user = next(user for user in snapshot["llm_external_users"] if user["user_id"] == "student-miami")
    assert student_user["provisioning_llm"] is provisioning_llm
    assert student_user["teams"] == ["team-1"]
    assert student_user["key_count"] == 1
    assert student_user["user_role"] == "internal_user_viewer"
    assert student_user["academy_config"] is snapshot["academies"][0]

    intruder_user = next(user for user in snapshot["llm_external_users"] if user["user_id"] == "intruder-miami")
    assert intruder_user["provisioning_llm"] is None
    assert intruder_user["teams"] == ["team-1", "team-other"]
    assert intruder_user["key_count"] == 0
    assert intruder_user["academy_config"] is snapshot["academies"][0]

    admin_user = next(user for user in snapshot["llm_external_users"] if user["user_id"] == "default_user_id")
    assert admin_user["user_role"] == "proxy_admin"
    assert admin_user["provisioning_llm"] is None


@patch("breathecode.provisioning.utils.llm_data_collection.get_llm_client")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningLLM.objects")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningAcademy.objects")
def test_collect_llm_data_assigns_academy_config_without_alert_emails(
    provisioning_academy_objects_mock,
    provisioning_llm_objects_mock,
    get_llm_client_mock,
):
    pa = _make_provisioning_academy_mock()
    _patch_provisioning_academy_query(provisioning_academy_objects_mock, [pa])
    _patch_active_provisioning_llms(provisioning_llm_objects_mock, [])

    client_mock = MagicMock()
    client_mock.list_keys.return_value = _list_keys_page(
        [
            {
                "token_id": "tok-orphan",
                "key_alias": "orphan",
                "user_id": None,
                "team_id": None,
            },
        ]
    )
    client_mock.list_users.return_value = _list_users_page([])
    client_mock.list_teams.return_value = {
        "teams": [
            {
                "team_id": "team-1",
                "members_with_roles": [],
            }
        ]
    }
    get_llm_client_mock.return_value = client_mock

    snapshot = collect_llm_data()

    assert snapshot["academies"][0]["alert_emails"] == []
    orphan_key = snapshot["keys"][0]
    assert orphan_key["academy_config"] is snapshot["academies"][0]


@patch("breathecode.provisioning.utils.llm_data_collection.get_llm_client")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningLLM.objects")
@patch("breathecode.provisioning.utils.llm_data_collection.ProvisioningAcademy.objects")
def test_collect_llm_data_enriches_team_without_member_budget(
    provisioning_academy_objects_mock,
    provisioning_llm_objects_mock,
    get_llm_client_mock,
):
    pa = _make_provisioning_academy_mock(team_id="team-orphan")
    _patch_provisioning_academy_query(provisioning_academy_objects_mock, [pa])
    _patch_active_provisioning_llms(provisioning_llm_objects_mock, [])

    client_mock = MagicMock()
    client_mock.list_keys.return_value = _list_keys_page([])
    client_mock.list_users.return_value = _list_users_page([])
    client_mock.list_teams.return_value = {
        "teams": [
            {
                "team_id": "team-orphan",
                "members_with_roles": [],
                "models": [],
                "metadata": {},
            },
            {
                "team_id": "team-1",
                "members_with_roles": [],
                "models": ["miami/gpt-4"],
                "spend": 0.0,
                "max_budget": 10.0,
                "metadata": {"team_member_budget_id": "budget-1"},
            },
        ]
    }
    client_mock.get_budgets_info.return_value = [{"budget_id": "budget-1", "max_budget": 3.5}]
    get_llm_client_mock.return_value = client_mock

    snapshot = collect_llm_data()

    orphan_team = next(team for team in snapshot["teams"] if team["team_id"] == "team-orphan")
    assert orphan_team["academy_config"] is snapshot["academies"][0]
    assert orphan_team["team_budget_duration"] is None
    assert orphan_team["team_member_budget_id"] is None
    assert orphan_team["member_max_budget"] is None
    assert orphan_team["member_budget_duration"] is None

    configured_team = next(team for team in snapshot["teams"] if team["team_id"] == "team-1")
    assert configured_team["academy_config"] is None
    assert configured_team["member_max_budget"] == 3.5

    client_mock.get_budgets_info.assert_called_once_with(budgets=["budget-1"])
