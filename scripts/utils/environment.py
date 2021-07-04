import os


def reset_environment():
    breathcode_dinamics_envs = [
        'LOG_LEVEL', 'CACHE_MIDDLEWARE_MINUTES', 'OLD_BREATHECODE_API',
        'CELERY_TASK_SERIALIZER', 'EMAIL_NOTIFICATIONS_ENABLED',
        'GITHUB_CLIENT_ID', 'GITHUB_SECRET', 'GITHUB_REDIRECT_URL',
        'SLACK_CLIENT_ID', 'SLACK_REDIRECT_URL', 'MAILGUN_API_KEY',
        'MAILGUN_FROM', 'GOOGLE_APPLICATION_CREDENTIALS',
        'ACTIVE_CAMPAIGN_KEY', 'ACTIVE_CAMPAIGN_URL', 'EVENTBRITE_KEY',
        'GOOGLE_SERVICE_KEY', 'GOOGLE_CLOUD_KEY', 'ROLLBAR_ACCESS_TOKEN',
        'SAVE_LEADS', 'API_URL', 'ENV', 'FACEBOOK_VERIFY_TOKEN',
        'FACEBOOK_CLIENT_ID', 'FACEBOOK_SECRET', 'FACEBOOK_REDIRECT_URL'
    ]

    for env in breathcode_dinamics_envs:
        if env in os.environ:
            del os.environ[env]


def test_environment():
    os.environ['ENV'] = 'test'


def celery_worker_environment():
    os.environ['CELERY_WORKER_RUNNING'] = 'True'
