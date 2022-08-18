# Environment variables

| name | description |
|---|---|
| ENV | Represents the current environment, can be `DEVELOPMENT`, `TEST`, and `PRODUCTION` |
| LOG_LEVEL | Represents the log level for the logging module, can be `NOTSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR` and `CRITICAL` |
| DATABASE_URL | Represents the connection string to the database, you can read more about [schema url](https://github.com/jazzband/dj-database-url#url-schema) |
| CACHE_MIDDLEWARE_MINUTES | Represents how long an item will last in the cache |
| API_URL | Represents the url of api rest |
| ADMIN_URL | Represents the url of frontend of the admin |
| APP_URL | Represents the url of frontend of the webside |
| REDIS_URL | Represents the url of Redis |
| CELERY_TASK_SERIALIZER | Represents the default serialization method to use. Can be pickle `json`, `yaml`, `msgpack` or any custom serialization methods |
| EMAIL_NOTIFICATIONS_ENABLED | Represents if the server can send notifications through email |
| SYSTEM_EMAIL | Represents the email of `Breathecode` for support |
| GITHUB_CLIENT_ID | Represents the client id used for the OAuth2 with `Github` |
| GITHUB_SECRET | Represents the secret used for the OAuth2 with `Github` |
| GITHUB_REDIRECT_URL | Represents the redirect url used for the OAuth2 with `Github` |
| SLACK_CLIENT_ID | Represents the client id used for the OAuth2 with `Slack` |
| SLACK_SECRET | Represents the secret used for the OAuth2 with `Slack` |
| SLACK_REDIRECT_URL | Represents the redirect url used for the OAuth2 with `Slack` |
| MAILGUN_API_KEY | Represents the api key used for the OAuth2 with `Mailgun` |
| MAILGUN_DOMAIN | Represents the domain of Breathecode that provided `Mailgun` |
| EVENTBRITE_KEY | Represents the key used for the OAuth2 with `Eventbrite` |
| FACEBOOK_VERIFY_TOKEN | Represents the verify token used for the OAuth2 with `Facebook` |
| FACEBOOK_CLIENT_ID | Represents the client id used for the OAuth2 with `Facebook` |
| FACEBOOK_SECRET | Represents the secret used for the OAuth2 with `Facebook` |
| FACEBOOK_REDIRECT_URL | Represents the redirect url used for the OAuth2 with `Facebook` |
| ACTIVE_CAMPAIGN_KEY | Represents the key used for the OAuth2 with `Active Campaign` |
| ACTIVE_CAMPAIGN_URL | Represents the domain of Breathecode that provided `Active Campaign` |
| GOOGLE_APPLICATION_CREDENTIALS | Represents the file will be saved the service account of `Google Cloud` |
| GOOGLE_SERVICE_KEY | Represents the content of the service account used for the OAuth2 with `Google Cloud` |
| GOOGLE_PROJECT_ID | Project ID on google cloud used for the integration of the entire API |
| GOOGLE_CLOUD_KEY | Represents the key used for the OAuth2 with `Google Cloud` |
| GOOGLE_CLIENT_ID | Represents the client id used for the OAuth2 with `Google Cloud` |
| GOOGLE_SECRET | Represents the secret used for the OAuth2 with `Google Cloud` |
| GOOGLE_REDIRECT_URL | Represents the redirect url used for the OAuth2 with `Google Cloud` |
| DAILY_API_KEY | Represents the api key used for the OAuth2 with `Daily` |
| DAILY_API_URL | Represents the domain of Breathecode that provided `Daily` |
| SAVE_LEADS | Represents if Breathecode will persist the leads |
| COMPANY_NAME | Represents the company name |
| COMPANY_CONTACT_URL | Represents the company contact url |
| COMPANY_LEGAL_NAME | Represents the company legal name |
| COMPANY_ADDRESS | Represents the company address |
| MEDIA_GALLERY_BUCKET | Represents the bucket for the media gallery |
| DOWNLOADS_BUCKET | Represents the bucket for the CSV files |
| PROFILE_BUCKET | Represents the bucket for profile avatars |
