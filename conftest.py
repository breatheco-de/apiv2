import pytest
import os


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    def urlopen_mock(self, method, url, *args, **kwargs):
        # this prevent a tester left pass a request to a third party service
        raise Exception(
            f'The test was about to {method} {self.scheme}://{self.host}{url} and this is a third party '
            'service')

    monkeypatch.setattr('urllib3.connectionpool.HTTPConnectionPool.urlopen', urlopen_mock)


# @pytest.fixture(autouse=True)
# def reset_environment(monkeypatch):
#     breathcode_dinamics_envs = [
#         'LOG_LEVEL', 'CACHE_MIDDLEWARE_MINUTES', 'OLD_BREATHECODE_API', 'CELERY_TASK_SERIALIZER',
#         'EMAIL_NOTIFICATIONS_ENABLED', 'GITHUB_CLIENT_ID', 'GITHUB_SECRET', 'GITHUB_REDIRECT_URL',
#         'SLACK_CLIENT_ID', 'SLACK_REDIRECT_URL', 'MAILGUN_API_KEY', 'MAILGUN_FROM',
#         'GOOGLE_APPLICATION_CREDENTIALS', 'ACTIVE_CAMPAIGN_KEY', 'ACTIVE_CAMPAIGN_URL', 'EVENTBRITE_KEY',
#         'GOOGLE_SERVICE_KEY', 'GOOGLE_CLOUD_KEY', 'ROLLBAR_ACCESS_TOKEN', 'SAVE_LEADS', 'API_URL', 'ENV',
#         'FACEBOOK_VERIFY_TOKEN', 'FACEBOOK_CLIENT_ID', 'FACEBOOK_SECRET', 'FACEBOOK_REDIRECT_URL',
#         'DATABASE_URL', 'REDIS_URL', 'MEDIA_GALLERY_BUCKET'
#     ]

#     for env in breathcode_dinamics_envs:
#         monkeypatch.delenv(env, raising=False)

#     monkeypatch.setenv('ENV', 'test', prepend=False)
