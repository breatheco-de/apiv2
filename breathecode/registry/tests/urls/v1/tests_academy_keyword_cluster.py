import random
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import capyc.pytest as capy
import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.admissions.models import Academy
from breathecode.registry.models import KeywordCluster
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers

from ...mixins import RegistryTestCase

# import breathecode.activity.tasks as activity_tasks
# from breathecode.assignments import tasks
# from breathecode.assignments.caches import TaskCache


UTC_NOW = timezone.now()


def get_serializer(self, task, user):
    return {
        "associated_slug": task.associated_slug,
        "created_at": self.bc.datetime.to_iso_string(task.created_at),
        "updated_at": self.bc.datetime.to_iso_string(task.updated_at),
        "github_url": task.github_url,
        "id": task.id,
        "live_url": task.live_url,
        "revision_status": task.revision_status,
        "task_status": task.task_status,
        "task_type": task.task_type,
        "title": task.title,
        "assignment_telemetry": task.telemetry.telemetry if task.telemetry else None,
        "description": task.description,
        "opened_at": self.bc.datetime.to_iso_string(task.opened_at) if task.opened_at else task.opened_at,
        "delivered_at": self.bc.datetime.to_iso_string(task.delivered_at) if task.delivered_at else task.delivered_at,
        "user": {"first_name": user.first_name, "id": user.id, "last_name": user.last_name},
        "cohort": {"id": task.cohort.id, "name": task.cohort.name, "slug": task.cohort.slug},
    }


# def database_item(academy, category, data={}):
#     return {
#         "academy_id": academy.id,
#         "learnpack_deploy_url": None,
#         "agent": None,
#         "assessment_id": None,
#         "asset_type": "PROJECT",
#         "author_id": None,
#         "authors_username": None,
#         "category_id": category.id,
#         "cleaning_status": "PENDING",
#         "cleaning_status_details": None,
#         "config": None,
#         "delivery_formats": "url",
#         "delivery_instructions": None,
#         "readme_updated_at": None,
#         "delivery_regex_url": None,
#         "description": None,
#         "difficulty": None,
#         "duration": None,
#         "external": False,
#         "gitpod": False,
#         "graded": False,
#         "html": None,
#         "id": 1,
#         "interactive": False,
#         "intro_video_url": None,
#         "is_seo_tracked": True,
#         "lang": None,
#         "last_cleaning_at": None,
#         "last_seo_scan_at": None,
#         "last_synch_at": None,
#         "last_test_at": None,
#         "optimization_rating": None,
#         "owner_id": None,
#         "github_commit_hash": None,
#         "preview": None,
#         "published_at": None,
#         "readme": None,
#         "readme_raw": None,
#         "readme_url": None,
#         "requirements": None,
#         "seo_json_status": None,
#         "slug": "",
#         "solution_url": None,
#         "solution_video_url": None,
#         "status": "NOT_STARTED",
#         "status_text": None,
#         "sync_status": None,
#         "test_status": None,
#         "title": "",
#         "url": None,
#         "visibility": "PUBLIC",
#         "with_solutions": False,
#         "with_video": False,
#         "is_auto_subscribed": True,
#         "superseded_by_id": None,
#         "enable_table_of_content": True,
#         "agent": None,
#         "learnpack_deploy_url": None,
#         "template_url": None,
#         "dependencies": None,
#         "preview_in_tutorial": None,
#         **data,
#     }


# @pytest.fixture(autouse=True)
# def setup(monkeypatch: pytest.MonkeyPatch, db):
#     monkeypatch.setenv("GOOGLE_CLIENT_ID", "123456.apps.googleusercontent.com")
#     monkeypatch.setenv("GOOGLE_SECRET", "123456")
#     monkeypatch.setenv("GOOGLE_REDIRECT_URL", "https://breathecode.herokuapp.com/v1/auth/google/callback")
#     monkeypatch.setattr("breathecode.services.google_apps.GoogleApps.__init__", MagicMock(return_value=None))
#     monkeypatch.setattr("breathecode.services.google_apps.GoogleApps.subscribe_meet_webhook", MagicMock())
#     monkeypatch.setattr(
#         "breathecode.services.google_apps.GoogleApps.get_user_info", MagicMock(return_value={"id": 123})
#     )


# Fixtures
# @pytest.fixture(autouse=True)
# def setup(db, monkeypatch):
#     monkeypatch.setattr("breathecode.registry.signals.keywordcluster_slug_modified.send_robust", MagicMock())
#     yield


@pytest.fixture
def academy(database: capy.Database):
    return database.create(academy=Academy)


@pytest.fixture
def keywordcluster(database: capy.Database, academy):
    return database.create(
        KeywordCluster, academy=academy, slug="test-cluster", title="Test Cluster", visibility="PUBLIC", lang="en"
    )


# @pytest.fixture
# def client():
#     return capy.Client()


# def test_no_token(database: capy.Database, client: capy.Client):
#     url = reverse_lazy("authenticate:google_callback")

#     response = client.get(url, format="json")

#     json = response.json()
#     expected = {"detail": "no-callback-url", "status_code": 400}

#     assert json == expected
#     assert response.status_code == status.HTTP_400_BAD_REQUEST

#     assert database.list_of("authenticate.Token") == []
#     assert database.list_of("authenticate.CredentialsGoogle") == []


# def test_no_url(database: capy.Database, client: capy.Client):
#     url = reverse_lazy("authenticate:google_callback") + "?state=url%3Dhttps://4geeks.com"

#     response = client.get(url, format="json")

#     json = response.json()
#     expected = {"detail": "no-user-token", "status_code": 400}

#     assert json == expected
#     assert response.status_code == status.HTTP_400_BAD_REQUEST

#     assert database.list_of("authenticate.Token") == []
#     assert database.list_of("authenticate.CredentialsGoogle") == []


class RegistryTestSuite(RegistryTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_without_auth(self):
        url = reverse_lazy("registry:keywordcluster")
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bc.database.list_of("registry.keywordcluster"), [])

    # def test_get_keywordcluster(client: capy.Client, database: capy.Database, keywordcluster: KeywordCluster):

    #     url = reverse_lazy("academy:keywordcluster")

    #     response = client.get(url, format="json")

    #     assert response.status_code == status.HTTP_200_OK
    #     assert len(response.data) > 0
    #     assert response.data[0]["slug"] == keywordcluster.slug
    #     assert response.data[0]["title"] == keywordcluster.title
    #     assert response.data[0]["lang"] == keywordcluster.lang
    #     assert database.list_of("academy.KeywordCluster") == [capy.Format.to_obj_repr(keywordcluster)]

    # def test_get_single_keywordcluster(client: capy.Client, database: capy.Database, keywordcluster: KeywordCluster):
    #     url = reverse_lazy("academy:keywordcluster") + f"/{keywordcluster.slug}/"

    #     response = client.get(url, format="json")

    #     assert response.status_code == status.HTTP_200_OK
    #     assert response.data["slug"] == keywordcluster.slug
    #     assert response.data["title"] == keywordcluster.title
    #     assert response.data["lang"] == keywordcluster.lang
    #     assert database.list_of("academy.KeywordCluster") == [capy.Format.to_obj_repr(keywordcluster)]
