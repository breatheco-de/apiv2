---
name: bc-authenticate-manage-github-org-users
description: Use when building or operating a staff frontend to list, schedule, sync, or recover academy GitHub organization memberships; do NOT use for Copilot seats, provisioning bills, or staff/student invites unrelated to GitHub org membership.
requires:
  - bc-authenticate-staff-authentication
---

# Skill: Manage Academy GitHub Organization Users

## When to Use

Use this skill when academy staff need a UI or API flow to **list** GitHub org members for an academy, **schedule** add/delete/ignore, **sync** membership with GitHub, **share** the org invitation URL, **read/update** academy GitHub settings, or **recover** stuck invite errors. Load [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) first for login, `Academy` header, and capability checks. Do not use this skill for GitHub Copilot seat provisioning, Codespaces/provisioning billing, or non-GitHub staff/student invitations.

## Concepts

- **Academy GitHub user**: One membership-intent record per academy and person for a shared GitHub organization. UI fields: `storage_status`, `storage_action`, `storage_log`, `username`, nested `user` and `github`.
- **Desired state vs sync**: Scheduling only sets intent (`PENDING` + `ADD`/`DELETE`, or `IGNORE`). GitHub invites/removals run when sync executes and `github_is_sync` is `true`.
- **Status × action (display matrix)**:
  - `PENDING` + `ADD` / `INVITE` / `DELETE` → waiting to apply (“Pending to add/invite/delete”).
  - `SYNCHED` + `ADD` → confirmed org member.
  - `SYNCHED` + `INVITE` → invite email sent; student may not have accepted yet.
  - `SYNCHED` + `DELETE` → removal applied (or skipped if another academy still needs them).
  - `SYNCHED` + `IGNORE` → leave alone on GitHub.
  - `ERROR` → last invite/delete call failed; read `storage_log` and the academy error log.
  - `UNKNOWN` + `IGNORE` → found in the org, not managed as a known student; keep ignored unless staff chooses otherwise.
- **Invite URL**: `https://github.com/orgs/{github_username}/invitation` using `github_username` from academy settings. Never hardcode an organization slug.
- **Two automation layers** (do not conflate):
  1. **Schedule intent (automatic):** Student becomes ACTIVE in a non–never-ending cohort → system queues `PENDING`+`ADD`. Leaves ACTIVE or cohort membership removed → system later queues `PENDING`+`DELETE`. Does **not** call GitHub by itself.
  2. **Apply to GitHub (periodic + on-demand):** When `github_is_sync` is `true`, a production scheduled job applies pending rows every few hours. Staff can also call `PUT .../github/user/sync` immediately. Without on-demand sync, rows may stay `PENDING` until the next scheduled run.
- **Sibling academies**: Several academies may share one `github_username`. Sync requires all of them to have `github_is_sync: true`. GitHub only deletes a login when no sibling academy still wants `ADD`/`INVITE`.
- **Academy header**: All `/academy/*` routes need `Authorization: Token <token>` and **`Academy: <numeric_id>`**.

## Workflow

1. **Authenticate and verify capabilities.** Complete [`bc-authenticate-staff-authentication`](../bc-authenticate-staff-authentication/SKILL.md) Track A, then Track B for the target academy. Capabilities: `get_github_user`, `update_github_user`, `sync_organization_users`, `get_academy_auth_settings`, and (to change settings) `crud_academy_auth_settings`.

2. **Load academy GitHub settings.** Call `GET /v1/auth/academy/settings`. Save `github_username` for the invite URL. Check `github_is_sync`. If `github_username` is empty, stop and tell staff to set the organization username before sharing invites. If `github_is_sync` is `false`, listing and scheduling still work, but sync will not update GitHub until it is enabled (and sibling academies sharing the org must also enable sync).

3. **Build the invite URL.** `https://github.com/orgs/{github_username}/invitation` from Step 2. Use this same URL for every user in that academy’s organization.

4. **List academy GitHub users.** Call `GET /v1/auth/academy/github/user` (paginated). Optional query: `like` (username, email, first/last name). Render status with the matrix above; surface `storage_log` in a tooltip or detail panel. `github` may be `null` if the user never connected GitHub; `user` may be `null` for unknown org members.

5. **Manually add an ACTIVE cohort user.** Call `POST /v1/auth/academy/github/user` with `cohort` and `user` (numeric ids). The user must be ACTIVE in that cohort and must already have GitHub credentials. This creates `PENDING`+`ADD`. Reload the list (Step 4) for the full GET shape.

6. **Bulk-schedule actions.** Call `PUT /v1/auth/academy/github/user?id=1,2,3` with `{ "storage_action": "ADD" | "DELETE" | "IGNORE" }`. `IGNORE` becomes `SYNCHED` immediately (no GitHub call). `ADD` / `DELETE` become `PENDING` and wait for sync.

7. **Sync on demand.** Call `PUT /v1/auth/academy/github/user/sync` (empty body) after scheduling, or when staff need immediate processing / ERROR recovery. Empty body: `200` success, `400` if sync is off or settings are invalid. Then reload the list (Step 4).

8. **Read the academy GitHub error log.** Call `GET /v1/auth/academy/settings/log`. Use messages such as “Error inviting member … to org” to spot duplicate-invite or API failures.

9. **Recover duplicate-invite / ERROR retry loops.** Sync only treats people already **accepted** into the org as members. A pending GitHub invitation is invisible to sync, so a second invite attempt often fails, sets `ERROR`, and the next sync requeues `ERROR` → `PENDING` and retries. The public `PUT` API **cannot** set `SYNCHED`+`INVITE` directly. To stop retries via API: `PUT` `{ "storage_action": "IGNORE" }` (becomes `SYNCHED`+`IGNORE` immediately). After the student accepts the GitHub invite (they appear as an org member), `PUT` `{ "storage_action": "ADD" }` and run Step 7 so sync confirms `SYNCHED`+`ADD`. Share the invite URL from Step 3 so the student can accept at GitHub.

10. **Update academy GitHub settings (when needed).** Call `PUT /v1/auth/academy/settings` with fields such as `github_username`, `github_is_sync`, `github_default_team_ids`, `github_owner`. Requires `crud_academy_auth_settings`. After changing `github_username`, rebuild the invite URL (Step 3).

11. **Handle UNKNOWN members.** After sync, org members not tied to academy students appear as `UNKNOWN`+`IGNORE`. Keep them ignored unless staff explicitly schedules `ADD` or `DELETE`.

## Endpoints

All paths below are under `/v1/auth`. Send `Accept-Language` (`en`, `es`) for translated errors where applicable. Every `/academy/` path requires **`Academy: <numeric_id>`**.

| Action | Method | Path | Required headers | Capability | Paginated |
|--------|--------|------|------------------|------------|-----------|
| Get academy auth settings | GET | `/v1/auth/academy/settings` | `Authorization`, **`Academy`** | `get_academy_auth_settings` | No |
| Update academy auth settings | PUT | `/v1/auth/academy/settings` | `Authorization`, **`Academy`** | `crud_academy_auth_settings` | No |
| Get GitHub error log | GET | `/v1/auth/academy/settings/log` | `Authorization`, **`Academy`** | `get_academy_auth_settings` | No |
| List GitHub users | GET | `/v1/auth/academy/github/user` | `Authorization`, **`Academy`** | `get_github_user` | **Yes** |
| Get one GitHub user | GET | `/v1/auth/academy/github/user/<githubuser_id>` | `Authorization`, **`Academy`** | `get_github_user` | No |
| Add GitHub user | POST | `/v1/auth/academy/github/user` | `Authorization`, **`Academy`** | `update_github_user` | No |
| Update GitHub user(s) | PUT | `/v1/auth/academy/github/user?id=<id>,<id>` or `/v1/auth/academy/github/user/<githubuser_id>` | `Authorization`, **`Academy`** | `update_github_user` | No |
| Sync organization users | PUT | `/v1/auth/academy/github/user/sync` | `Authorization`, **`Academy`** | `sync_organization_users` | No |

### Get academy settings — response sample (200)

```json
{
  "id": 12,
  "academy": {
    "id": 4,
    "slug": "downtown-miami",
    "name": "Downtown Miami"
  },
  "github_username": "4GeeksAcademy",
  "github_owner": {
    "id": 88,
    "email": "owner@example.com",
    "first_name": "Org",
    "last_name": "Owner"
  },
  "google_cloud_owner": null,
  "github_default_team_ids": "1234567,7654321",
  "github_is_sync": true,
  "github_error_log": [
    {
      "msg": "Error inviting member student@example.com to org: already invited",
      "at": "2025-01-28 12:35:14.857450+00:00"
    }
  ],
  "learnpack_owner": null,
  "learnpack_features": {},
  "learnpack_org_id": null
}
```

Invite URL for this academy: `https://github.com/orgs/4GeeksAcademy/invitation`.

### Update academy settings — request sample

```json
{
  "github_username": "4GeeksAcademy",
  "github_is_sync": true,
  "github_default_team_ids": "1234567",
  "github_owner": 88
}
```

### Get settings log — response sample (200)

```json
[
  {
    "at": "2025-01-28 02:02:41.228000+00:00",
    "msg": "Error inviting member lord@valdomero.com to org: Unable to communicate with Github API"
  },
  {
    "at": "2025-01-28 12:35:14.857450+00:00",
    "msg": "Error inviting member lord@valdomero.com to org: Unable to communicate with Github API"
  }
]
```

Empty log returns `[]`. Missing settings returns `400` with slug `no-github-auth-settings`.

### List GitHub users — response sample (200, paginated)

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 501,
      "academy": {
        "id": 4,
        "name": "Downtown Miami",
        "slug": "downtown-miami"
      },
      "user": {
        "id": 320,
        "username": "maria",
        "first_name": "Maria",
        "last_name": "Lopez",
        "email": "maria.lopez@example.com"
      },
      "username": "marialopez",
      "storage_status": "PENDING",
      "storage_action": "ADD",
      "storage_log": [
        {
          "msg": "User was manually added",
          "at": "2025-06-01 15:04:05.123456+00:00"
        }
      ],
      "storage_synch_at": null,
      "created_at": "2025-06-01T15:04:05Z",
      "github": {
        "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
        "name": "Maria Lopez",
        "username": "marialopez"
      }
    }
  ]
}
```

Query example: `GET /v1/auth/academy/github/user?like=maria`.

### Add GitHub user — request sample

```json
{
  "cohort": 45,
  "user": 320
}
```

### Add GitHub user — response sample (200)

POST returns the create serializer fields (not the full GET shape). Reload with GET for nested `github` / `storage_status`.

```json
{
  "id": 501,
  "user": 320,
  "storage_action": "ADD"
}
```

### Update GitHub user — request sample

```json
{
  "storage_action": "DELETE"
}
```

Use `IGNORE` to stop automated retries without calling GitHub (`SYNCHED` immediately). Use `ADD` or `DELETE` to queue work (`PENDING`).

### Sync organization users — request

Empty body. Success: `200` with empty body. Failure examples: `settings-not-found`, `github-sync-off`, or sibling academies not all synced (`not-everyone-in-synch`).

## Edge Cases

| Observation | What to do |
|-------------|------------|
| `github_is_sync` is `false` or sync returns `github-sync-off` | Tell staff to enable sync in settings (`PUT` Step 10). Do not claim GitHub was updated. |
| Sync error: all academies with the same org must enable sync (`not-everyone-in-synch`) | List sibling academies sharing `github_username` and enable `github_is_sync` on each before syncing. |
| User has no GitHub credentials | POST fails (“No github credentials found”). Sync marks such rows `ERROR` with log “This user needs connect to github”. Ask the student to connect GitHub, then re-queue `ADD` and sync. |
| POST: user not ACTIVE in the given cohort | `400` / cohort not found. Pick an ACTIVE cohort membership for that user. |
| POST: user already has a row for this academy | Validation error “User already belongs to the organization”. Use `PUT` to change `storage_action` instead. |
| `ERROR` after invite; error log shows invite failure / already invited | Duplicate-invite loop. Share invite URL; `PUT` `IGNORE` to stop retries; after accept, `PUT` `ADD` + sync. The API cannot set `SYNCHED`+`INVITE` directly. |
| Row stays `PENDING` after staff action | Scheduled job or Step 7 sync has not run yet, or sync is off. Trigger sync or wait for the periodic job. |
| `UNKNOWN` + `IGNORE` users appear after sync | Discovered in the org. Keep ignored unless staff explicitly schedules `ADD` or `DELETE`. |
| DELETE while student still ACTIVE in another cohort | Backend blocks removal (`still-active`). Do not force-delete from the UI; wait until they are inactive everywhere in that academy. |
| Whitelisted users cannot be removed | Backend may reject removal. Leave as `ADD` / do not schedule `DELETE` for those accounts (whitelist is not managed by these list endpoints). |

## Checklist

1. Staff auth completed; `Academy` header set; capabilities verified (`get_github_user`, `update_github_user`, `sync_organization_users`, `get_academy_auth_settings`).
2. `GET /v1/auth/academy/settings` returned `github_username`; invite URL is `https://github.com/orgs/{github_username}/invitation` (not a hardcoded org).
3. List endpoint returns paginated results; UI maps `storage_status` × `storage_action` and shows `storage_log`.
4. Manual add / bulk `ADD`/`DELETE`/`IGNORE` behave as documented (`IGNORE` synched immediately; others `PENDING`).
5. UI exposes on-demand sync and does not claim sync only happens on button click (periodic job also applies when `github_is_sync` is true).
6. Error log endpoint is available; duplicate-invite recovery uses `IGNORE` → accept invite → `ADD` + sync.
7. If sync is off or siblings disagree, UI surfaces the error and does not pretend GitHub changed.
