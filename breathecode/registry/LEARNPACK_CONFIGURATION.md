# LearnPack: `learn.json`, asset fields, and 4Geeks.com UI

[Spanish version / Versión en español](./LEARNPACK_CONFIGURATION.es.md)

This document explains how repository **`learn.json`** maps to **`Asset`** fields in the API (`apply_learn_config` in `models.py`) and how those fields drive the lesson/exercise UI in the website (`ProjectInstructions.jsx`, `ModalToCloneProject.jsx`).

> **Reminder — `grading` (`incremental` vs `isolated`):** For **Breathecode** assets, both values produce the same `interactive` / `gitpod` outcome. You should still choose the one that matches **the kind of work students do in LearnPack**—step-by-step / cumulative packs suit **`incremental`**; packs where each item is self-contained suit **`isolated`**. That decision follows **`projectType`** and how the repo is structured (**exercise** vs **project**, tutorials, etc.), not only what the 4Geeks UI shows.

## Files and fields (summary)

| Source | What it controls |
|--------|------------------|
| **`learn.json` in GitHub** | Synced on pull into `asset.config`; `apply_learn_config` updates title, preview, `interactive`, `gitpod`, delivery, technologies, etc. |
| **`learnpack_deploy_url` on the Asset** | **Not** read from `learn.json` today. Set in the Breathecode registry (admin/API) when the pack is published to LearnPack Cloud. Enables the **iframe / “start interactive”** flow when the cohort has SaaS. |
| **Cohort** | `available_as_saas` (iframe); provisioning **vendors** (e.g. GitHub Codespaces) loaded per academy. |

Config filenames pulled from the repo (see `pull_learnpack_asset`): `learn.json`, `.learn/learn.json`, `bc.json`, `.learn/bc.json`.

## `interactive` and `gitpod` from `learn.json`

The API **does not** read a top-level `interactive` key from `learn.json`. It derives `interactive` and `gitpod` from **`grading`**, **`projectType`**, **`localhostOnly`**, and an optional trailing **`gitpod`** flag.

Relevant logic in `Asset.apply_learn_config` (`registry/models.py`):

1. If there is **no** `grading` and `projectType` is **not** `"tutorial"` → `interactive = False`.
2. If **`projectType` is `"tutorial"`** → `interactive = True`, and `gitpod` depends on `localhostOnly`.
3. If **`grading` is `"incremental"` or `"isolated"`** → `interactive = True`, and `gitpod =` (not `localhostOnly`).
4. Finally, if **`gitpod` is present** in JSON (`true` / `false`) → it **overwrites** `gitpod`.

For **both** flags to end up **true** (typical “cloud + local modal” setup):

```json
{
  "projectType": "exercise",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true
}
```

(`"isolated"` behaves the same as `"incremental"` for these two flags—but **pick the value that fits how the pack is authored**; see the reminder above.)

To force **interactive** but **no** cloud provisioning in the modal, use e.g. `localhostOnly: true` and/or `"gitpod": false` (see UI section below).

### `grading`: incremental vs isolated

For the **Breathecode** asset flags, both values are equivalent: they both set `interactive = True` and the same `gitpod` rule. **As an author, treat the choice as LearnPack semantics:** **`incremental`** when exercises build on previous steps or one evolving codebase; **`isolated`** when each exercise is independent. Match that to **`projectType`** and the actual brief you give students (small drills vs multi-step projects)—do not pick at random just because the website treats them the same for `interactive` / `gitpod`.

### `template_url`

Only applies to **`PROJECT`** assets. If `template_url` appears in `learn.json` for an **EXERCISE**, the API logs an error and does not apply it as a template. For projects, use e.g. `"self"` or a real template repository URL.

### `projectType` in `learn.json`

Use `"exercise"` or `"project"` as appropriate. `"tutorial"` is a special `projectType` that also activates the interactive branch (with `gitpod` driven by `localhostOnly`).

## `learnpack_deploy_url` (registry only)

Stored on **`Asset.learnpack_deploy_url`**. It is **not** populated from `learn.json` in `apply_learn_config`.

It is required (together with cohort SaaS and allowlists) for the UI to show the **recommended “start interactive exercise/project”** button that loads LearnPack in-context, **alongside** “open locally”.

See `ProjectInstructions.jsx`:

- `startWithLearnpack = learnpack_deploy_url && cohortSession.available_as_saas && slug not in no-learnpack list`

Excluded slugs: `app/public/no-learnpack-in-cloud.json`.

## Website UI behavior

### Dual buttons: “Start interactive …” + “Open locally”

Shown when **`startWithLearnpack`** is true (deploy URL + SaaS + slug allowed). The second button opens **`ModalToCloneProject`**.

### Modal: provisioning (“open in the cloud”) vs clone locally

From `ModalToCloneProject.jsx`:

- **`showProvisioningLinks`** = `provisioningVendors.length > 0` **and** `currentAsset.gitpod === true`.
- **`isInteractive`** = `currentAsset.interactive` (drives OS/steps vs direct vendor links).
- **Codespaces** links are built from a **GitHub** repository URL (`currentAsset.url` / `readme_url`); they must not be a generic LearnPack public URL alone.

So:

- **Cloud options in the modal** need **`gitpod: true`** on the asset (from `learn.json` as above) and the academy/cohort must return **provisioning vendors** including Codespaces (or Gitpod).
- **Direct Codespace/Gitpod buttons** inside the modal require **`selectedOption === 'provisioning_vendors'`** and **`isInteractive`** when showing the shortcut list (see component).

### Single CTA: “Start exercise” / “Start project” (no iframe) — modal only, cloud + local

Use this when you want **no** in-context LearnPack iframe (**“Start interactive …”**) but students should still open **`ModalToCloneProject`** and choose **provisioning** (e.g. Codespaces / Gitpod) **or** **open locally**.

In **`ButtonsHandler`** (`ProjectInstructions.jsx`), when **`startWithLearnpack`** is **false**, the UI shows **one** button. Its label comes from **`common:learnpack.start-asset`** (e.g. **“Start exercise”** for `EXERCISE`, **“Start project”** for `PROJECT`). That button opens the **same** modal as **“Open locally”** in the dual-button layout; inside the modal, **`showProvisioningLinks`** and **`isForOpenLocaly`** still follow **`gitpod`**, **`interactive`**, and provisioning vendors as above.

**Make the iframe / dual header go away:** keep **`startWithLearnpack`** false. Typical options:

- Do **not** set **`learnpack_deploy_url`** on the **Asset** in the registry (no LearnPack Cloud URL for the iframe flow), **or**
- Add the asset **`slug`** to **`app/public/no-learnpack-in-cloud.json`** so the iframe path is skipped even if a deploy URL exists (e.g. URL kept for other tools but not the recommended in-app interactive button).

Still required for cloud + local **inside the modal**: asset **`interactive`** and **`gitpod`** via **`learn.json`** (e.g. `grading` + `localhostOnly: false` + `gitpod: true` as in the full-modal snippet), **cohort** with **`available_as_saas`** so the usual private flow can load academy **provisioning vendors**, and a valid **GitHub repo** URL on the asset for Codespaces.

**Example (`learn.json`)** — same flags as a cloud-capable interactive exercise; the difference is **registry only** (no deploy URL, or slug in `no-learnpack-in-cloud.json`):

```json
{
  "slug": "example-exercise-modal-only",
  "title": "Example (modal only, no iframe)",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "exercise",
  "difficulty": "EASY",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "technologies": ["javascript"]
}
```

**Registry:** leave **`learnpack_deploy_url`** unset (or use **`no-learnpack-in-cloud.json`** as above). After sync, the lesson shows a single **Start exercise** (or **Start project**) control that opens the modal with **open in the cloud** / **open locally** when vendors and URLs allow it.

### “Only start interactive” (single CTA)

If **`startWithLearnpack`** is true, the current UI **always** shows **both** the interactive start and “open locally”. Hiding the second button is **not** configurable via `learn.json` alone.

### “Start interactive + open locally” but **no** cloud in the modal

Keep **`learnpack_deploy_url`** + SaaS for the two header buttons. Set the asset **`gitpod`** to **`false`** via `learn.json`, e.g.:

```json
{
  "projectType": "exercise",
  "grading": "incremental",
  "localhostOnly": true,
  "gitpod": false
}
```

Provisioning links will not appear (`showProvisioningLinks` false); local flow still works when `interactive` is true.

## Example snippets

### Exercise — full modal with cloud + local (after sync)

```json
{
  "slug": "example-exercise",
  "title": "Example",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "exercise",
  "difficulty": "EASY",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "technologies": ["typescript"],
  "editor": { "agent": "vscode", "version": "5.0" }
}
```

Plus **`learnpack_deploy_url`** on the asset in the registry if you need the iframe + dual buttons.

### Project — same flags, with template

```json
{
  "slug": "example-project",
  "title": "Example project",
  "description": "…",
  "preview": "https://example.com/preview.png",
  "projectType": "project",
  "difficulty": "INTERMEDIATE",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true,
  "template_url": "self",
  "technologies": ["react"]
}
```

## Related code

- `breathecode/registry/models.py` — `Asset.apply_learn_config`, `learn_config_to_metadata`, `to_learn_config`
- `breathecode/registry/actions.py` — `pull_learnpack_asset`
- `app/src/components/GuidedExperience/ProjectInstructions.jsx`
- `app/src/components/GuidedExperience/ModalToCloneProject.jsx`

## Historical note

The older example in `registry/README.md` uses fields like `graded` / `intro` as strings. Prefer the current shape (`grading`, `video`, `projectType`, etc.) consistent with `apply_learn_config` and tests in `registry/tests/test_asset_learn_config.py`.
