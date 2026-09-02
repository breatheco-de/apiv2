# Registry asset fields

Use this catalog with [`SKILL.md`](../SKILL.md). Write academy assets through `POST`/`PUT /v1/registry/academy/asset`. Resolve **category** ids and **technology** slugs from the lookup endpoints in the skill before sending them.

For PROJECT/EXERCISE, a GitHub pull of `learn.json` can overwrite `interactive`, `gitpod`, `with_video`, `with_solutions`, `title`, `description`, `technologies`, delivery fields, and `agent`. Prefer repo config as source of truth for those after sync.

## Identity

| Field | Create | Update | Meaning |
|---|---|---|---|
| `slug` | Required | Optional (slugified) | Globally unique identifier (all academies). Lowercase hyphens. Used on 4geeks.com. Alias collision → 400. |
| `title` | Send it | Yes | Display title. `learn.json` can overwrite on pull. |
| `asset_type` | Required | Yes | `LESSON`, `ARTICLE`, `QUIZ`, `EXERCISE`, `PROJECT`, `STARTER`, `VIDEO`. Do not invent other values. Type changes GitHub sync, LearnPack, and delivery. |
| `lang` | Required | Yes | Language of this row. Store `us`, `es`, `it`. Send `en` and the API stores `us`. Category language must match (`us`/`en` count as the same). |

## Classification

| Field | Create | Update | Meaning |
|---|---|---|---|
| `category` | Required (numeric **id**, or `"uncategorized"`) | Numeric **id** only; not null | Academy-scoped grouping. Get ids from `GET /v1/registry/academy/category`. `"uncategorized"` is **POST only**. PUT cannot null category; langs must match. List filter `?category=` uses **slugs**, not ids. Read: `{ id, slug, title }`. |
| `technologies` | Optional slug array | **Full replace** | Tech stack tags. Slugs from `GET /v1/registry/academy/technology`. `[]` clears. Omit to leave unchanged. Unknown slug → 400. No API to create a technology. Read: **parent slugs only**. Prefer parent slugs. `learn.json` can overwrite. |
| `seo_keywords` | Optional slugs | Yes | SEO keywords from `GET /v1/registry/academy/keyword`. Prefer at most two. Not the same as `technologies`. |

## Publication

| Field | Create | Update | Meaning |
|---|---|---|---|
| `status` | Optional; default `NOT_STARTED` | Yes | `NOT_STARTED`, `PLANNING`, `WRITING`, `DRAFT`, `OPTIMIZED`, `PUBLISHED`. Public website shows **`PUBLISHED` only**. There is **no `DELETED`**. `PUBLISHED` (or `visibility` `PUBLIC`/`UNLISTED`) requires `test_status` `OK` or `WARNING`. First publish sets `published_at`; leaving published clears it. Role `content_writer` may only change status, and not to `PUBLISHED`. |
| `visibility` | Optional; default `PUBLIC` | Yes | Which **academies** can see this internally. Not SEO. `PUBLIC` = other academies. `UNLISTED` = same academy, direct link. `PRIVATE` = owner/author. List GET defaults to `PUBLIC`. |
| `feature` | Optional; default `false` | Yes | Marketing only. If true, eligible for website **landing pages**. Does not change student runtime, LearnPack, or grading. |

## How the student opens it

| Field | Default | Meaning |
|---|---|---|
| `external` | `false` | Content is **not** built with 4Geeks or LearnPack. Opens in a new window. Cannot push to GitHub. List GET hides these unless `external=true` or `both`. Do not use as the primary path together with `interactive`. |
| `interactive` | `false` | LearnPack-enabled: step-by-step package (`learn.json`), not a static markdown page. Independent of `gitpod`. Pull can overwrite from `learn.json` (`grading` `isolated`/`incremental`, or `projectType: tutorial`). |
| `gitpod` | `false` | Cloud IDE allowed (Gitpod **or** Codespaces). Historical name; not Gitpod-only. Student “open in the cloud” needs this true plus academy provisioning vendors. Independent of `interactive`. Typical LearnPack: both true. Local-only LearnPack: `interactive` true, `gitpod` false. Pull can overwrite (`gitpod`, `localhostOnly`). |
| `enable_table_of_content` | `true` | Show a table of contents at the top of a **lesson**. Mostly LESSON/ARTICLE. Markdown frontmatter `table_of_contents` can overwrite on pull. Not computed from headings. |
| `agent` | `null` | How to recommend opening an exercise/project. `vscode` = open in VS Code (different student instructions). `standalone` = open from the terminal. From `learn.json` `editor.agent` on pull. |

## Solutions and media

| Field | Meaning |
|---|---|
| `with_solutions` | A model solution exists (repo and/or per-step solutions). Often set from `learn.json` (`solution`, `video.solution`, `videoSolutions`). Pair with `solution_url` / `solution_video_url`. Not “teacher already graded this.” |
| `with_video` | Video is attached (intro and/or solution). Often set from `learn.json` (`video-id`, `video.intro`, `video.solution`, `videoSolutions`). Filter: `?video=true`. Pair with `intro_video_url` / `solution_video_url`. |
| `graded` | **Deprecated.** All assets are graded with AI. Do **not** set this to enable grading. Do **not** treat it as a telemetry switch. Ignore unless the user explicitly asks to change the stored boolean. LearnPack `config.grading` (`isolated`/`incremental`) is a different field: step mode, not this checkbox. |

## URLs and content

| Field | Meaning |
|---|---|
| `url` | Repository or destination URL. Setting `readme_url` on update also sets `url` to the GitHub repo root (`https://github.com/org/repo`). |
| `readme_url` | GitHub file used to sync markdown. Lessons: that blob URL. PROJECT/EXERCISE/QUIZ: `README.md` (English) or `README.<lang>.md`. If set on create and `readme_raw` is empty, create queues an async pull. |
| `readme_raw` | Source markdown to save. **`readme` is read-only** — never send `readme`. |
| `html` | Generated HTML. Do not send as the way to edit content; use `readme_raw` plus clean/pull. |
| `preview` | Social-share image URL. `null` on update deletes the cloud thumbnail. `learn.json` `preview` can overwrite. |
| `preview_in_tutorial` | Image shown on 4geeks.com **before the tutorial starts**. Not the same as `preview`. |
| `intro_video_url` | Intro video URL. Can come from `learn.json` video fields. |
| `solution_video_url` | Solution video URL. |
| `solution_url` | URL to solution code. Can come from `learn.json` `solution`. |
| `solution_readme` | Solution markdown. System-managed; not the primary write path. |
| `description` | Public/SEO description. Not the writer brief. |
| `requirements` | Internal brief for copywriters: what the lesson should be about. Not student instructions. |

## LearnPack / cloud

| Field | Meaning |
|---|---|
| `config` | Snapshot of `learn.json` (and quiz JSON). Source of truth for PROJECT/EXERCISE after sync. Updating some fields while `config` exists can set `sync_status=NEEDS_RESYNC` and may queue a GitHub push if `is_auto_subscribed`. Do not hand-edit unless the user asks. |
| `learnpack_deploy_url` | Public LearnPack **cloud** URL, only if published to LearnPack cloud. Drives in-app “start interactive” / iframe. Empty = no cloud iframe from this field. |
| `learnpack_id` | LearnPack numeric id. Integration; do not invent. |
| `manifest` | Snapshot of the LearnPack Cloud published manifest. Read-only for this skill. |
| `template_url` | PROJECT only: template used to open the project. If the project has no template, value should be `"self"`. Other types should not set this. |
| `dependencies` | Auto from `package.json` / `pyproject.toml` etc. Example: `python=3.10,node=16.0`. Do not invent. |

## Project delivery (especially `PROJECT`)

| Field | Meaning |
|---|---|
| `delivery_instructions` | Tell students **how** to deliver. Used in review and AI context. |
| `delivery_formats` | Comma-separated formats. Default `url`. Examples: `url`, `image/png`, `application/pdf`. |
| `delivery_regex_url` | Allowed URL pattern. Only used when `url` is among `delivery_formats`. |
| `flag_seed` | Auto-generated for PROJECT CTF/delivery flags. Not writable. Do not send. |

## Difficulty and time

| Field | Meaning |
|---|---|
| `difficulty` | `BEGINNER`, `EASY`, `INTERMEDIATE`, `HARD`. Optional. `learn.json` can overwrite (uppercased). |
| `duration` | Estimated hours (integer). Optional. `learn.json` can overwrite. |

## Translations and versions

| Field | Meaning |
|---|---|
| `all_translations` | Other language versions of the **same** content. Write an array of asset **slugs**. Link every member of the set (include self). Create can omit `category` only if the first translation already has a category in this asset’s language. |
| `superseded_by` | Newer version of this asset (tech deprecation, e.g. React Router v5 → v6). Null = this is latest. Write the **new asset’s id**. Cannot supersede itself. Cannot point at something that already supersedes a different asset. Read also includes previous-version fields. |
| `assets_related` | Prep content (lessons/exercises/projects to do **before** this one). Not translations and not technologies. |

## GitHub sync (do not fake)

| Field | Meaning |
|---|---|
| `is_auto_subscribed` | Default `true`. If true, GitHub push webhooks update this asset. Set `false` while making local edits you do not want overwritten. |
| `sync_status` | System: `PENDING`, `ERROR`, `OK`, `WARNING`, `NEEDS_RESYNC`. Not editorial status. |
| `test_status` | System result of integrity tests. Same enum. `OK` or `WARNING` required before `PUBLISHED` / public visibility. Do not invent. |
| `status_text` | Human feedback from sync/test. System-written. |
| `last_synch_at`, `last_test_at`, `readme_updated_at`, `github_commit_hash`, `github_activity_logs` | Audit. Read only for this skill. |
| `allow_contributions` | Whether the **repo** is public (`true`) or private (`false`). About GitHub visibility, not student submissions. |

## People and academy

| Field | Meaning |
|---|---|
| `author` | Who wrote it. Not necessarily GitHub owner. |
| `owner` | User with GitHub permission to update the repo. Needed for push. |
| `authors_username` | Comma-separated GitHub usernames. |
| `academy` | Owning academy. On academy POST it is set from the `Academy` header. Unclaimed (`null`) assets are claimed by the academy on PUT. Do not send `academy` in the body. GET academy asset returns a numeric id; create response nests `{id, name}`. |

## SEO machinery (optional)

| Field | Meaning |
|---|---|
| `is_seo_tracked` | Include in SEO scans. |
| `optimization_rating`, `last_seo_scan_at`, `seo_json_status` | Filled by SEO analysis. Do not invent scores. |

## System (read; do not send on a normal create)

`id`, `readme`, `html`, `config`, `manifest`, `flag_seed`, `sync_status`, `test_status`, `status_text`, `telemetry_stats`, `github_activity_logs`, `learnpack_id`, `dependencies`, `graded`, `assessment` (linked quiz for `QUIZ`), `cleaning_status`, `cleaning_status_details`, `last_cleaning_at`, `created_at`, `updated_at`, `published_at`, and all `last_*` timestamps.

Bulk PUT to the collection URL requires each object’s `id`. PUT by slug also binds to that id.

## Minimum create body

```json
{
  "slug": "intro-to-python",
  "title": "Introduction to Python",
  "asset_type": "LESSON",
  "lang": "us",
  "category": 12
}
```

Optional on create: `technologies` (slugs), `readme_url`, `status`, `visibility`, and booleans that actually apply (`external`, `interactive`, `gitpod`, `enable_table_of_content`, `feature`, `with_solutions`, `with_video`). Omit `graded`.
