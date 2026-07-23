# verify_email contextual copy and academy overrides

This document explains how the `verify_email` notification uses `UserInvite` context and how academies can override each variant via `AcademyNotifySettings`.

For the general notification registry and settings API, see [NOTIFICATION_REGISTRY.md](./NOTIFICATION_REGISTRY.md).

## When it is sent

`verify_email` is sent after subscribe / waiting-list signup creates a user from a `UserInvite` (task `verify_user_invite_email`), and on some invite resend paths when the email is not yet validated.

Templates: `breathecode/authenticate/templates/verify_email.html` and `.txt`.

## Context resolution (`UserInvite`)

Priority (first match wins):

1. `event_slug` → load `Event` by slug (any academy) → `CONTEXT_NAME` = `Event.title` (never the slug; if title empty → unslugify; if event missing → try next)
2. `asset_slug` → `Asset.title` (same rules)
3. `course` → `CourseTranslation.title` for user lang (fallback first translation / unslugify of course slug)
4. `cohort` → `cohort.name`
5. else → `generic`

Code: `breathecode.authenticate.actions.get_verify_email_copy(invite, lang)`.

Injected into the email `data` dict:

- `CONTEXT_TYPE`: `event` | `asset` | `course` | `cohort` | `generic`
- `CONTEXT_NAME`: human-readable title (empty for generic)
- `LANG`: recipient language (used to pick language-specific overrides)
- Default strings for every variant: `SUBJECT_EVENT`, `MESSAGE_EVENT`, `SUBJECT_ASSET`, `MESSAGE_ASSET`, `SUBJECT_COURSE`, `MESSAGE_COURSE`, `SUBJECT_COHORT`, `MESSAGE_COHORT`, plus generic `SUBJECT` / `MESSAGE`

Defaults use the placeholder `{CONTEXT_NAME}` so academy overrides can reuse it. Defaults are already bilingual via `translation(lang, en=..., es=...)`.

## Send pipeline

1. Caller builds `data` via `get_verify_email_copy` (+ `LINK`, etc.), including `LANG`.
2. `send_email_message("verify_email", …, academy=…)` applies `AcademyNotifySettings` overrides for that `LANG`.
3. `apply_verify_email_variant(data)` picks final `SUBJECT` / `MESSAGE` from the active `CONTEXT_TYPE` and replaces `{CONTEXT_NAME}`.
4. Django templates render `{{ subject }}` and `{{ MESSAGE }}`.

**Important:** empty `AcademyNotifySettings` (`template_variables: {}`) overrides nothing. Only explicit keys change behavior.

## Per-variant overrides

Do **not** rely on a single `template.verify_email.subject` for all cases — that would flatten every signup reason. Use variant keys:

| Context | Subject key | Message key |
|---------|-------------|-------------|
| Event | `SUBJECT_EVENT` | `MESSAGE_EVENT` |
| Asset / tutorial | `SUBJECT_ASSET` | `MESSAGE_ASSET` |
| Course | `SUBJECT_COURSE` | `MESSAGE_COURSE` |
| Cohort | `SUBJECT_COHORT` | `MESSAGE_COHORT` |
| Generic | `subject` / `SUBJECT` | `MESSAGE` |

## Per-language overrides

Append a 2-letter language code to the key:

- `template.verify_email.SUBJECT_EVENT.en`
- `template.verify_email.SUBJECT_EVENT.es`
- `template.verify_email.MESSAGE_ASSET.en`
- `template.verify_email.MESSAGE_ASSET.es`

### Resolution priority (for a given variable)

1. Override for the recipient language (`…SUBJECT_EVENT.es` when `LANG=es` / `es-ES`)
2. Legacy override **without** language (`…SUBJECT_EVENT`) — applies to all langs
3. Code default from `get_verify_email_copy` for that language

**Never** reuse another language's override. If only `.en` is set, Spanish users get the **code ES default**, not the English override text.

### Example (bilingual event copy)

```json
{
  "template_variables": {
    "template.verify_email.SUBJECT_EVENT.en": "Finish setup to join the \"{CONTEXT_NAME}\" event",
    "template.verify_email.SUBJECT_EVENT.es": "Finaliza tu registro para asistir a \"{CONTEXT_NAME}\"",
    "template.verify_email.MESSAGE_EVENT.en": "To join \"{CONTEXT_NAME}\", set a password and validate your account.",
    "template.verify_email.MESSAGE_EVENT.es": "Para unirte a \"{CONTEXT_NAME}\", crea tu contraseña y valida tu cuenta."
  },
  "disabled_templates": []
}
```

### Example (only English overridden)

```json
{
  "template_variables": {
    "template.verify_email.SUBJECT_ASSET.en": "Open \"{CONTEXT_NAME}\" now"
  }
}
```

- User `en` → `"Open \"{CONTEXT_NAME}\" now"`
- User `es` → code default: `Finaliza tu registro para aprender "{CONTEXT_NAME}"` (etc.)

API: `GET` then merge then `PUT /v1/notify/academy/settings` (full `template_variables` replace).

### Precedence (overall)

1. Academy lang-specific `template.verify_email.*`
2. Academy legacy (no lang) / `global.*`
3. Code defaults from `get_verify_email_copy`
4. Academy model branding fields / env (via `get_template_content`)

After overrides, the active variant is always selected using `CONTEXT_TYPE`.

## Registry

Variables are declared in `breathecode/notify/registry/verify_email.json`. Only registered variable names are valid for template-specific overrides (the `.en` / `.es` suffix is validated separately as a language code).

## Related code

- `breathecode/authenticate/actions.py` — `get_verify_email_copy`
- `breathecode/notify/actions.py` — `apply_verify_email_variant`, `send_email_message`
- `breathecode/notify/models.py` — `AcademyNotifySettings.get_all_overrides_for_template(slug, lang=…)`
- `breathecode/authenticate/tasks.py` — `verify_user_invite_email`
- `breathecode/authenticate/views.py` — invite resend path that sends `verify_email`
