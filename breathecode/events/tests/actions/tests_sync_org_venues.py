"""
Test /answer
"""
from datetime import datetime
from unittest.mock import patch
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
    MAILGUN_PATH,
    MAILGUN_INSTANCES,
    apply_mailgun_requests_post_mock,
    SLACK_PATH,
    SLACK_INSTANCES,
    apply_slack_requests_request_mock,
)
from ..mixins import EventTestCase
from ...actions import sync_org_venues


class SyncOrgVenuesTestSuite(EventTestCase):
    """Test /answer"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_sync_org_venues_without_cohort(self):
        """Test /answer without auth"""
        model = self.generate_models(organization=True)

        try:
            sync_org_venues(model['organization'])
        except Exception as e:
            self.assertEquals(str(e), (
                'First you must specify to which academy this organization belongs'
            ))

    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_sync_org_venues_without_cohort(self):
        """Test /answer without auth"""
        model = self.generate_models(organization=True, academy=True)

        try:
            sync_org_venues(model['organization'])
        except Exception as e:
            self.assertEquals(str(e),
                              ('The path you requested does not exist.'))
