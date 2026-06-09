# LearnPack: `learn.json` and registry assets (API-focused)

This reference describes how repository **`learn.json`** (and aliases) maps into **`Asset`** fields after sync (`apply_learn_config` on the API). Use it together with **`GET /v1/registry/asset/{slug}`** response fields (`config`, `asset_type`, `graded`, URLs, etc.) when reviewing **PROJECT** deliveries.

Config filenames synced from repos include: **`learn.json`**, **`.learn/learn.json`**, **`bc.json`**, **`.learn/bc.json`**.

## Summary

| Source | What it controls |
|--------|------------------|
| **`learn.json` in Git** | After sync, stored in **`asset.config`**; drives **`Asset`** title, preview, **`interactive`**, **`gitpod`**, technologies, and related fields via **`apply_learn_config`**. |
| **`learnpack_deploy_url` on Asset** | **Not** read from **`learn.json`**. Set on the asset in the registry when publishing to LearnPack Cloud. |
| **`grading` (`incremental` vs `isolated`)** | For Breathecode-derived **`interactive`** / **`gitpod`** flags, both behave the same in the API. Choose **`incremental`** for cumulative / step-by-step work; **`isolated`** for independent exercises — match **`projectType`** and how the repo is structured. |

## `interactive` and `gitpod` from `learn.json`

The API **does not** use a top-level **`interactive`** key from **`learn.json`**. It derives **`interactive`** and **`gitpod`** from **`grading`**, **`projectType`**, **`localhostOnly`**, and an optional **`gitpod`** override.

Typical rules (see **`Asset.apply_learn_config`** in the codebase):

1. If there is **no** **`grading`** and **`projectType`** is **not** **`"tutorial"`** → **`interactive = False`**.
2. If **`projectType` is `"tutorial"`** → **`interactive = True`**, and **`gitpod`** follows **`localhostOnly`**.
3. If **`grading`** is **`"incremental"`** or **`"isolated"`** → **`interactive = True`**, and **`gitpod =`** (not **`localhostOnly`**).
4. If **`gitpod`** is present in JSON (**`true`** / **`false`**) → it **overwrites** **`gitpod`**.

Example producing **`interactive`** and **`gitpod`** true:

```json
{
  "projectType": "exercise",
  "grading": "incremental",
  "localhostOnly": false,
  "gitpod": true
}
```

### `template_url`

- Applies to **`PROJECT`** assets. If **`template_url`** appears for an **EXERCISE**, the API logs an error and does not apply it as a template.
- For projects, values may include **`"self"`** or a real template repository URL.

### `projectType`

Use **`"exercise"`** or **`"project"`** as appropriate. **`"tutorial"`** is special and activates the interactive branch with **`gitpod`** driven by **`localhostOnly`**.

## Example project snippet (`learn.json`)

```json
{
  "slug": "example-project",
  "title": "Example project",
  "description": "Build a small React app.",
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

## Historical note

Older examples sometimes used fields like **`graded`** / **`intro`** as strings. Prefer shapes consistent with **`apply_learn_config`** (e.g. **`grading`**, **`video`**, **`projectType`**) as reflected in **`asset.config`** after sync.
