---
name: bc-monitoring-create-new-report
description: Use when adding a new monitoring report type end-to-end (generation + read API registry metadata); do NOT use for only reading report data or debugging existing report rows.
requires: []
---

# Skill: Create Monitoring Report

## When to Use
- Use this skill when implementing a new `monitoring` report type (new model/report generator + API registry entry).
- Use it when `python manage.py generate_report <report_type>` must support a new type.
- Use it when `/v1/monitoring/report*` must expose a new `report_type`.
- Do NOT use this skill for read-only consumption of existing reports.
- Do NOT use this skill for unrelated domains outside `breathecode.monitoring`.

## Workflow
1. Define the report data model under `breathecode/monitoring/reports/<report_type>/models.py`.
2. Implement a generator class in `breathecode/monitoring/reports/<report_type>/actions.py` extending `BaseReport`.
3. Register command generation by adding the new class in `breathecode/monitoring/management/commands/generate_report.py` `REPORT_REGISTRY`.
4. Add list/detail serializers in `breathecode/monitoring/serializers.py` for the new report model.
5. Register API metadata in `breathecode/monitoring/reports/api_registry.py`:
   - `slug`, `label`, `description`
   - `model`, `list_serializer`, `detail_serializer`
   - `filters`, `sort_fields`, `default_sort`
   - `supports_detail`, `supports_summary`, `summary_builder`, `date_field` (as needed)
6. Validate list/detail/summary behavior through existing generic monitoring report endpoints in `breathecode/monitoring/views.py` and `breathecode/monitoring/urls.py` (no new endpoint path required).
7. Add tests for report generation command and report API behavior.
8. Run focused tests for new report files plus current monitoring report URL tests.

## Endpoints
- **Method:** `GET`
- **Path:** `/v1/monitoring/report`
- **Purpose for this skill:** Verify your new `report_type` appears in discovery metadata.

**Response fields to verify**
```json
{
  "slug": "new-report-slug",
  "filters": ["academy", "date"],
  "sort_fields": ["created_at", "-created_at"],
  "supports_detail": true,
  "supports_summary": true
}
```

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}`
- **Purpose for this skill:** Verify list serialization and filters for the new report.

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}/{report_id}`
- **Purpose for this skill:** Verify detail serializer output for one row.

- **Method:** `GET`
- **Path:** `/v1/monitoring/report/{report_type}/summary`
- **Purpose for this skill:** Verify summary builder output shape if summary is enabled.

## Edge Cases
- New report missing in discovery: confirm `api_registry.py` has an entry in `REPORT_API_REGISTRY`.
- Command rejects report type: confirm `generate_report.py` `REPORT_REGISTRY` includes it.
- Unsupported filter/sort errors: ensure `filters` and `sort_fields` in registry match intended query behavior.
- Empty default list response: if `date_field` is configured, list defaults to latest date; verify test fixtures include report rows for at least one date.
- Summary fails: set `supports_summary=False` when no `summary_builder` exists, or implement the builder.

## Checklist
1. [ ] Added report model + migrations under `monitoring/reports/<report_type>`.
2. [ ] Implemented `BaseReport` subclass with fetch/process/save flow.
3. [ ] Registered report in `generate_report.py` `REPORT_REGISTRY`.
4. [ ] Added serializers and API registry config for the report type.
5. [ ] Verified discovery/list/detail/summary endpoints with the new `report_type`.
6. [ ] Added automated tests for command and API behavior.
7. [ ] Ran focused tests successfully before finishing.
