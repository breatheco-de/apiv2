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
| SAVE_LEADS | Represents if Breathecode will persist the leads |
| COMPANY_NAME | Represents the company name |
| COMPANY_CONTACT_URL | Represents the company contact url |
| COMPANY_LEGAL_NAME | Represents the company legal name |
| COMPANY_ADDRESS | Represents the company address |
| MEDIA_GALLERY_BUCKET | Represents the bucket for the media gallery |
| DOWNLOADS_BUCKET | Represents the bucket for the CSV files |
| PROFILE_BUCKET | Represents the bucket for profile avatars |
