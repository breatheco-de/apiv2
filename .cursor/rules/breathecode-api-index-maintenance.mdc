---
name: breathecode-api-index-maintenance
description: Use this rule when creating, renaming, or deleting a BreatheCode API skill, when a cross-domain workflow is discovered or changed, OR when any BreatheCode API endpoint is added, modified, or removed. Ensures skills and BOTH API indexes stay in sync with the actual API. Do NOT use for general skill authoring — use skill-authoring.mdc for that.
---

# BreatheCode API indexes maintenance

These files are the routing entry points for BreatheCode API skills:

- **Staff:** [`docs/agent-docs/skills/breathecode-staff-api-index/SKILL.md`](docs/agent-docs/skills/breathecode-staff-api-index/SKILL.md)
- **Student (learner):** [`docs/agent-docs/skills/breathecode-student-api-index/SKILL.md`](docs/agent-docs/skills/breathecode-student-api-index/SKILL.md)

They must reflect the current skill inventory and the API. Follow these rules whenever the API code or skill inventory changes.

---

## Which index to update (persona rule)

| Situation | Update |
|-----------|--------|
| New or changed skill is **academy-scoped** (`/academy/`, `Academy` header, staff capabilities) or appears only in staff workflows | **Staff** index (`breathecode-staff-api-index`) — domain map and/or **Common Cross-Domain Workflows** |
| New or changed skill documents **learner-scoped** routes (`/me/`, `/user/me/`, or public join/catalog without staff) or you add a learner cross-domain workflow | **Student** index (`breathecode-student-api-index`) — domain map and/or **Common Cross-Domain Workflows (learner)** |
| Domain-wide auth, payments, or other behavior affects **both** personas | **Both** indexes (at least the **Domain Map** row for that domain; add workflow rows where each persona needs them) |
| New API **domain app** (new `/v1/<app>/` surface) | **Staff** index: always add a **Domain Map** row. **Student** index: add a row only if learners have first-class routes in that app; otherwise the student index **Staff-first domains** section should point readers to the staff index |

Never create, rename, or delete a skill without updating the **appropriate** index(es) in the same change.

---

## When to update skills and the indexes

Triggers: **API changes** and **skill changes**. Both require updates to relevant skills and the correct index(es) before the task is considered complete.

### Triggered by API changes

Update relevant skills and the index(es) when any of the following happen to the BreatheCode API codebase:

- A new endpoint is added
- An existing endpoint's method, path, required fields, or response shape changes
- An endpoint is deprecated or removed
- A new domain app is added to the API
- A field is renamed or its type changes

**Do not treat API changes as code-only tasks.** Every API change has a skill obligation — see [Rule 6: API changed](#rule-6-api-changed).

### Triggered by skill changes

Update one or both index files when any of the following happen:

- A new domain skill is created
- An existing skill is renamed
- A skill is deleted
- A new cross-domain workflow is discovered or documented
- An existing cross-domain workflow changes

---

## Skill self-containment

Skills under `docs/agent-docs/skills/` are the **only** agent-facing API workflow source.

- A skill must be **self-contained**: include workflow steps, endpoints, required headers, and JSON payloads so the agent can complete the task without loading external markdown docs.
- **Allowed cross-references:** other skills (`bc-<domain>-<verb>-<resource>`) via `requires` in frontmatter or relative links to `SKILL.md` files in the skills tree.
- **Forbidden in skills:** links or pointers to `docs/agent-docs/*.md`, `docs/llm-docs/*.md`, or any file that is not a skill (`SKILL.md`). Examples: `BC_STAFF_INVITES.md`, `manage_roles.md`, `SYLLABUS.md`.
- **When a skill would reference a human doc:** create a new skill or extend an existing one with the needed workflow and endpoints; update the appropriate index in the same change.
- **Indexes** may link to skills and to the staff/student index. Indexes must **not** link to human markdown docs for workflow detail (same rule as skills).

For full authoring rules (structure, payloads, anti-patterns), see [`skill-authoring.mdc`](skill-authoring.mdc).

---

## Rule 1: New skill created

When a new skill is created under `docs/agent-docs/skills`:

1. Identify the domain from the skill name (e.g. `bc-admissions-create-cohort` → domain is `bc-admissions`, bc stands for breathecode).
2. Using the [persona rule](#which-index-to-update-persona-rule), open **`breathecode-staff-api-index/SKILL.md`**, **`breathecode-student-api-index/SKILL.md`**, or **both**.
3. Confirm the domain already exists in the **Domain Map** table of each index you are updating. If not, add a new row: domain name, one-line description (scoped to **staff** vs **learner** wording per file), and `bc-domain-*` as the skill pattern.
4. Do **not** use the domain map as an inventory of every skill file — the wildcard pattern (`bc-admissions-*`) is the default. Optional: one linked canonical use-case skill per row where the staff index already sets precedent (e.g. assignment domain).
5. If the new skill introduces a cross-domain dependency, add a row to **Common Cross-Domain Workflows** in the **staff** index, the **student** index, or **both**, matching who would perform that workflow.

---

## Rule 2: Skill renamed

When an existing skill is renamed:

1. Search the **Common Cross-Domain Workflows** tables in **both** index files for the old skill name.
2. Replace every occurrence of the old name with the new name.
3. If the domain prefix changed, check the **Domain Map** in each file that contained the old domain.

---

## Rule 3: Skill deleted

When a skill is deleted:

1. Search the **Common Cross-Domain Workflows** tables in **both** index files for references to the deleted skill name.
2. Remove or update the affected workflow rows.
3. If the deleted skill was the only representation of a domain in that index’s domain map, remove or adjust the domain row (staff vs student may differ).

---

## Rule 4: New cross-domain workflow discovered

When writing a use-case skill and you discover it requires loading skills from more than one domain:

1. Add a row to **Common Cross-Domain Workflows** in the **staff** index, **student** index, or **both**, per the [persona rule](#which-index-to-update-persona-rule).
2. The row must include: the plain-language user request, and all skill names (or domain wildcards) that must be loaded, with a brief note explaining why each is needed.
3. Keep the user request description generic enough to match how a real user would phrase it — not implementation-specific (e.g. "Enroll a student in a cohort", not "POST to /v1/admissions/academy/cohort/user").

---

## Rule 5: Index accuracy check

Before finishing any task that involved creating or modifying skills OR API endpoints, verify:

1. [ ] Every skill created or renamed is accounted for in the correct index(es) (domain map row exists where that persona applies).
2. [ ] Every cross-domain dependency introduced is listed in the appropriate **Common Cross-Domain Workflows** table(s).
3. [ ] No skill names in workflow tables are stale (pointing to deleted or renamed skills).
4. [ ] Domain maps do not list every skill file — wildcard `bc-domain-*` rows are the default (optional single canonical linked skill per row only where already established).
5. [ ] If an API endpoint was changed, the relevant skill(s) have been updated to reflect the change.
6. [ ] If a new API domain was added, a new domain row exists in the **staff** index; the **student** index is updated if learners use that app.
7. [ ] New or edited skills contain no links to non-skill markdown files.
8. [ ] Any removed doc reference is replaced by a skill link or inlined API detail.

---

## Rule 6: API changed

When an API endpoint is added, modified, or removed:

1. **Identify the domain** from the endpoint path (e.g. `/v1/admissions/...` → `bc-admissions` domain).
2. **Find all skills in that domain** by scanning `docs/agent-docs/skills` for files and folders matching `bc-admissions-*`.
3. **For each affected skill**, check whether the changed endpoint is documented in its `## Endpoints` section.
4. **If the endpoint is documented in a skill**, update that skill:
   - Changed method or path → update the endpoint reference
   - New required field → add it to the body example and required fields list
   - Removed field → remove it and check if any workflow step references it
   - Removed endpoint → remove it from the skill; if it was the only endpoint, flag the skill as needing replacement or deletion
   - Changed response shape → update any step that reads from the response (e.g. "save the returned `id`")
5. **If no skill exists yet for the changed endpoint**, do nothing for the skill file — but if the endpoint is part of a cross-domain workflow in either index, note that the workflow may be affected. If the workflow was previously documented only in a human `.md` file, **create a skill** instead of linking that doc from an existing skill.
6. **If a new domain app was added to the API**, add a new row to the **staff** index **Domain Map**; add to the **student** index only if learner routes exist, per the [persona rule](#which-index-to-update-persona-rule).

**Do not silently skip this step.** If you are unsure which skill covers a changed endpoint, scan the skills directory and check. If no skill covers it, explicitly note this to the user.

---

## What each index must NOT contain

- Full endpoint documentation (that belongs in domain skills)
- Implementation internals (ORM, class names) unless a skill already does for debugging
- Workflow step-by-step instructions for a single use case (those belong in use-case skills)
- Speculative cross-domain workflows that have not been confirmed by an actual skill
- References to Django Admin or non-API tools (see skill-authoring rules)
- Links to human markdown documentation files for workflow or endpoint detail (use skills only)

---

## Format reference

**Domain map row format:**

```markdown
| **domain-name** | One-line description of what this domain covers | `bc-domain-name-*` |
```

**Cross-domain workflow row format:**

```markdown
| User-facing request description | `skill-one` + `skill-two` (reason why skill-two is needed) |
```
