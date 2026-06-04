---
name: ""
overview: ""
todos: []
isProject: false
---

# Media Category: is_manageable_by_academy and academy FK

## Semantic (per your description)

- `**is_manageable_by_academy = True**`: Category is for API internal use. Academies **cannot** create/update/delete it, but **can** associate their media to it. These categories must have `academy = null`.
- `**is_manageable_by_academy = False**` (and optionally `academy` set): Category can be managed by academies. When `academy` is set, only that academy can manage it; when `academy` is null, it remains a global category (current behavior).
- `**academy` FK**: Owner of the category. Only non-system categories can have an academy; system categories must have `academy = null`.

Spelling: use `**is_manageable_by_academy**` (standard "manageable").

---

## 1. Model changes ([breathecode/media/models.py](breathecode/media/models.py))

- Add `**is_manageable_by_academy**`: `BooleanField(default=False)`. When `True`, category is API-internal and academies cannot manage it (only assign media to it).
- Add `**academy**`: `ForeignKey(Academy, on_delete=models.CASCADE, null=True, blank=True)`. Owner of the category; must be null when `is_manageable_by_academy=True`.
- **Slug uniqueness**: Remove `unique=True` from `slug` and add a `**UniqueConstraint**` on `(slug, academy)` (e.g. `UniqueConstraint(fields=["slug", "academy"], name="media_category_slug_academy_unique")`). This allows:
  - One system category per slug (`academy=null`).
  - One category per slug per academy when `academy` is set.
- Add `**clean()**` (or a `full_clean()` call on save) to enforce: if `is_manageable_by_academy` is `True`, then `academy` must be `null`; if `academy` is set, then `is_manageable_by_academy` must be `False`.

---

## 2. Migration

- New migration in `breathecode/media/migrations/`:
  - Add `is_manageable_by_academy` (default `False`) and `academy` (nullable FK).
  - Remove unique constraint from `slug` and add `UniqueConstraint` on `["slug", "academy"]`.
- **Data**: Existing rows get `is_manageable_by_academy=False`, `academy=null` so behavior stays "global" and editable by anyone with `crud_media` until you introduce system categories.

---

## 3. Serializers ([breathecode/media/serializers.py](breathecode/media/serializers.py))

- **GetCategorySerializer**: Expose `is_manageable_by_academy` and `academy` (id/slug/name or null).
- **CategorySerializer** (create/update): Include `academy` (optional; from request/context). Do **not** allow setting `is_manageable_by_academy` from academy requests (only for system/internal creation, e.g. admin or scripts). On create with academy context, set `academy=academy_id`, `is_manageable_by_academy=False`.

---

## 4. Category views ([breathecode/media/views.py](breathecode/media/views.py))

- **List (get)**
  - Base filter so the requesting academy sees: system categories (`academy__isnull=True`) and own categories (`academy_id=academy_id`):  
  `Category.objects.filter(Q(academy__isnull=True) | Q(academy_id=academy_id))`.
  - **Querystring filters** (optional; apply on top of base filter):
    - `**is_manageable_by_academy**`: Boolean. If present, filter by `is_manageable_by_academy=true` or `false` (e.g. `?is_manageable_by_academy=true` for only system/internal categories).
    - `**academy_isnull**`: Boolean. If present, filter by whether `academy` is null (e.g. `?academy_isnull=true` for only system/global categories, `?academy_isnull=false` for only academy-owned).
  - Parse query params (e.g. `request.GET.get("is_manageable_by_academy")`, `request.GET.get("academy_isnull")`) and apply the corresponding `.filter()` so the endpoint remains a single "fetch all [visible] categories" with optional narrowing.
- **get_slug**
Resolve by slug in academy context: categories where `slug=category_slug` and `(academy_id=academy_id | academy_id__isnull=True)`. If you need a single result, define precedence (e.g. prefer academy-owned over system, or first match).
- **get_id**
No change (id is globally unique).
- **post (create)**
  - Only allow creating categories with `is_manageable_by_academy=False` (academies cannot create system categories).
  - Set `academy` from request (e.g. `academy_id` from `capable_of` / header).
  - Slug uniqueness is already enforced by `(slug, academy)` constraint.
- **put (update)**
Allow only when the category is **manageable by this academy**: e.g. `category.academy_id == academy_id`. If `category.is_manageable_by_academy` or `category.academy_id` is not the requesting academy, return 403.
- **delete**
Same rule as put: only when `category.academy_id == academy_id`.

---

## 5. process_media ([breathecode/media/settings.py](breathecode/media/settings.py))

When resolving categories by slug from `meta["categories"]`, restrict to categories the uploading academy can use:

- System: `academy__isnull=True`.
- Academy's own: `academy_id=academy_id`.

Use: `Category.objects.filter(slug__in=meta["categories"]).filter(Q(academy_id=academy_id) | Q(academy_id__isnull=True))` so media is not assigned to another academy's category. Handle `academy_id` being null for user uploads (e.g. only system categories: `Q(academy_id__isnull=True)`).

---

## 6. Media bulk put (categories assignment)

When updating media and setting `categories`, ensure the provided category IDs/slugs are only those the academy is allowed to use (system + own). In the view or serializer that applies the category set, validate that each category is in the same "visible" set as in list (system or `academy_id=academy_id`); otherwise return 400/403.

---

## 7. Admin ([breathecode/media/admin.py](breathecode/media/admin.py))

- **MediaCategoryAdmin**: Add `is_manageable_by_academy` and `academy` to `list_display` and `list_filter` so system vs academy-owned categories are visible and filterable.

---

## 8. Tests

- **Model**: Test `clean()` / constraint (e.g. `is_manageable_by_academy=True` forces `academy=null`; `(slug, academy)` uniqueness).
- **GenerateModelsMixin** ([breathecode/tests/mixins/generate_models_mixin/media_models_mixin.py](breathecode/tests/mixins/generate_models_mixin/media_models_mixin.py)): Support `is_manageable_by_academy` and `academy` in category creation so existing tests can set system vs academy-owned categories.
- **Category list (get)**: Test that without querystring the list returns visible categories (system + academy's); test `?is_manageable_by_academy=true|false` and `?academy_isnull=true|false` narrow results correctly.
- **Category views**: Add/update tests for get_slug with academy scope, post (academy set, no system creation), put/delete (403 when category is system or another academy's).
- **process_media**: Test that only system or same-academy categories are resolved by slug when `academy_id` is present.
- **Upload / media tests**: Adjust any category assertions to include the new fields and, where relevant, academy scope.

---

## List endpoint and querystring (summary)

- **Endpoint**: Same as today (e.g. `GET /v1/media/category` or equivalent with Academy header). No new endpoint; enhance the existing "fetch all categories" list.
- **Querystring**:
  - `is_manageable_by_academy`: `true` | `false` — filter by the boolean field.
  - `academy_isnull`: `true` | `false` — filter by `academy__isnull`.
- Both are optional; when omitted, list returns all categories visible to the academy (system + own). When provided, apply the corresponding filter on top of the visibility filter.

---

## Files to touch (summary)


| Area          | File                                                                                                       |
| ------------- | ---------------------------------------------------------------------------------------------------------- |
| Model         | [breathecode/media/models.py](breathecode/media/models.py)                                                 |
| Migration     | New in `breathecode/media/migrations/`                                                                     |
| Serializers   | [breathecode/media/serializers.py](breathecode/media/serializers.py)                                       |
| Views         | [breathecode/media/views.py](breathecode/media/views.py) (CategoryView list + get_slug, post, put, delete) |
| process_media | [breathecode/media/settings.py](breathecode/media/settings.py)                                             |
| Admin         | [breathecode/media/admin.py](breathecode/media/admin.py)                                                   |
| Tests         | Category list (with querystring), get_slug, post, put, delete, process_media, mixin                        |


