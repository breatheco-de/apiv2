---
name: bc-notify-manage-academy-slackintegration
description: Use when academy staff need to connect Slack, run manual syncs, and monitor Slack sync health for students/cohorts; do NOT use for generic notifications or non-Slack messaging workflows.
requires: []
---

# Skill: Manage Academy Slack Integration

## When to Use

Use this skill when the user asks to connect an academy to Slack using manual credentials, manually sync Slack users/channels, or inspect sync status/errors/last sync times. Use it for team-level and individual student/cohort sync actions. Do NOT use it for email/SMS notifications, webhook subscriptions, or unrelated admissions operations.

## Concepts

- **Slack Team**: The Slack workspace linked to one academy.
- **User mapping**: A Slack user is linked when their Slack profile email matches a student user email in that academy's cohorts.
- **Cohort mapping**: A Slack channel is linked when the channel `name_normalized` matches the cohort slug.
- **Manual sync**: Staff-triggered async sync endpoint to force refresh without waiting for automatic jobs.

## Workflow

1. **Verify linked team.** Call `GET /v1/notify/slack/team` and filter by academy if needed.
2. **Configure Slack credentials manually.** Call `POST /v1/notify/academy/slack/team/<team_id>/credentials` with a Slack bot token and metadata (`team_name`, optional `app_id`, `bot_user_id`, `authed_user`).
3. **Check credentials status.** Call `GET /v1/notify/academy/slack/team/<team_id>/credentials` and confirm `configured=true`.
4. **Run manual team syncs.** Trigger users and channels sync separately:
   - `POST /v1/notify/academy/slack/team/<team_id>/sync/users`
   - `POST /v1/notify/academy/slack/team/<team_id>/sync/channels`
5. **Run manual individual syncs when needed.**
   - User: `POST /v1/notify/academy/slack/team/<team_id>/sync/user/<slack_user_id>`
   - Cohort: `POST /v1/notify/academy/slack/team/<team_id>/sync/cohort/<cohort_id>`
6. **Monitor sync health.** Poll:
   - Team summary: `GET /v1/notify/academy/slack/team/<team_id>/sync/status`
   - User status: `GET /v1/notify/academy/slack/team/<team_id>/sync/user/<slack_user_id>`
   - Cohort status: `GET /v1/notify/academy/slack/team/<team_id>/sync/cohort/<cohort_id>`
7. **Fix data source mismatches through admissions endpoints.** If sync is incomplete:
   - ensure students are in the academy cohort (`/v1/admissions/academy/cohort/user`)
   - ensure cohort slug matches Slack channel name (`/v1/admissions/academy/cohort`).

## Endpoints

| Action | Method | Path | Headers | Body | Response |
|---|---|---|---|---|---|
| List linked Slack teams | GET | `/v1/notify/slack/team` | `Authorization` | Query optional: `academy=<slug>` | Paginated list of Slack teams |
| Get team credentials status | GET | `/v1/notify/academy/slack/team/<team_id>/credentials` | `Authorization`, `Academy: <academy_id>` | — | `configured` boolean + metadata; token is never returned |
| Configure team credentials | POST/PUT | `/v1/notify/academy/slack/team/<team_id>/credentials` | `Authorization`, `Academy: <academy_id>` | `token`, optional `team_name`, `app_id`, `bot_user_id`, `authed_user` | `200` configured response |
| Trigger team users sync | POST | `/v1/notify/academy/slack/team/<team_id>/sync/users` | `Authorization`, `Academy: <academy_id>` | — | `202` accepted + metadata |
| Trigger team channels sync | POST | `/v1/notify/academy/slack/team/<team_id>/sync/channels` | `Authorization`, `Academy: <academy_id>` | — | `202` accepted + metadata |
| Trigger single user sync | POST | `/v1/notify/academy/slack/team/<team_id>/sync/user/<slack_user_id>` | `Authorization`, `Academy: <academy_id>` | — | `202` accepted + metadata |
| Get single user sync status | GET | `/v1/notify/academy/slack/team/<team_id>/sync/user/<slack_user_id>` | `Authorization`, `Academy: <academy_id>` | — | User-team sync status object |
| Trigger single cohort sync | POST | `/v1/notify/academy/slack/team/<team_id>/sync/cohort/<cohort_id>` | `Authorization`, `Academy: <academy_id>` | — | `202` accepted + metadata |
| Get single cohort sync status | GET | `/v1/notify/academy/slack/team/<team_id>/sync/cohort/<cohort_id>` | `Authorization`, `Academy: <academy_id>` | — | Cohort-channel sync status object |
| Get team sync status | GET | `/v1/notify/academy/slack/team/<team_id>/sync/status` | `Authorization`, `Academy: <academy_id>` | — | Team summary + users/channels counters |
| Manage cohort membership (source data) | GET/POST/PUT/DELETE | `/v1/admissions/academy/cohort/user` | `Authorization`, `Academy: <academy_id>` | Depends on method | Cohort-user assignment result |
| Manage cohorts/slugs (source data) | GET/POST/PUT | `/v1/admissions/academy/cohort` | `Authorization`, `Academy: <academy_id>` | Depends on method | Cohort object(s) |

**Configure team credentials — request (POST `/v1/notify/academy/slack/team/<team_id>/credentials`):**
```json
{
  "token": "xoxb-1234567890-abcdef",
  "team_name": "4Geeks Academy",
  "app_id": "A123456",
  "bot_user_id": "U0BOT123",
  "authed_user": "U0ADMIN123"
}
```

**Credentials status — response (200):**
```json
{
  "configured": true,
  "team_id": "T01ABC",
  "team_name": "4Geeks Academy",
  "app_id": "A123456",
  "bot_user_id": "U0BOT123",
  "authed_user": "U0ADMIN123",
  "updated_at": "2026-03-23T18:21:31.123Z"
}
```

**Trigger team users sync — response (202):**
```json
{
  "status": "accepted",
  "sync_type": "users",
  "team_id": 7
}
```

**Trigger single user sync — response (202):**
```json
{
  "status": "accepted",
  "sync_type": "user",
  "team_id": 7,
  "slack_user_id": "U09ABC123"
}
```

**Team sync status — response (200):**
```json
{
  "id": 7,
  "slack_id": "T01ABC",
  "name": "4Geeks Academy",
  "sync_status": "COMPLETED",
  "sync_message": null,
  "synqued_at": "2026-03-23T18:21:31.123Z",
  "users": {
    "total": 120,
    "completed": 110,
    "incompleted": 10,
    "last_synqued_at": "2026-03-23T18:21:30.555Z"
  },
  "channels": {
    "total": 18,
    "completed": 15,
    "incompleted": 3,
    "last_synqued_at": "2026-03-23T18:20:40.111Z"
  }
}
```

**Single user status — response (200):**
```json
{
  "sync_status": "INCOMPLETED",
  "sync_message": "Slack user exists but is not linked to this team",
  "synqued_at": null
}
```

GET list note: `GET /v1/notify/slack/team` is paginated.

For `/academy/` endpoints, always send `Academy` header. Error messages may be translated; send `Accept-Language` (`en`, `es`) to control language.

## Edge Cases

- **Missing or wrong academy scope:** API returns 403 or academy validation error. Retry with correct `Academy` header and permissions.
- **Team not found in academy:** Returns `slack-team-not-found`. Use a team id that belongs to the current academy.
- **User sync stays incomplete:** Usually user email does not map to any student in academy cohorts. Fix enrollment/email first, then re-run user sync.
- **Cohort sync stays incomplete:** Usually no channel matches cohort slug. Rename channel or cohort slug, then re-run cohort sync.
- **Missing Slack credentials:** Sync tasks fail if team credentials were not configured for that Slack team.
- **Automatic sync exists but not enough:** Use manual sync endpoints for targeted recovery or verification.

## Checklist

1. Confirm academy Slack team exists (`GET /v1/notify/slack/team`).
2. Configure credentials via `POST /v1/notify/academy/slack/team/<team_id>/credentials`.
3. Verify `configured=true` using `GET /v1/notify/academy/slack/team/<team_id>/credentials`.
4. Trigger team users/channels sync and verify `202` accepted responses.
5. Trigger individual user/cohort sync for failed mappings.
6. Poll team and individual status endpoints until completion or clear error.
7. Fix admissions source data (cohort memberships/slugs) when status is incomplete.
8. Re-run manual sync endpoints and confirm status/messages are healthy.
