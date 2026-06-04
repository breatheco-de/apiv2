from dataclasses import dataclass
from datetime import date
from collections import defaultdict
from typing import Any, Callable

from django.db.models import Avg, Count, Model, Q, QuerySet

from breathecode.monitoring.reports.acquisition.models import AcquisitionReport
from breathecode.monitoring.reports.churn.models import ChurnAlert, ChurnRiskReport
from breathecode.monitoring.serializers import (
    AcquisitionReportDetailSerializer,
    AcquisitionReportListSerializer,
    ChurnRiskReportDetailSerializer,
    ChurnRiskReportListSerializer,
)

SummaryBuilder = Callable[[QuerySet[Any], list[int]], dict[str, Any]]


@dataclass(frozen=True)
class ReportApiConfig:
    slug: str
    label: str
    description: str
    model: type[Model]
    list_serializer: type
    detail_serializer: type
    filters: dict[str, dict[str, Any]]
    sort_fields: tuple[str, ...]
    default_sort: str
    supports_detail: bool
    supports_summary: bool
    summary_builder: SummaryBuilder | None = None
    date_field: str | None = None


def _build_churn_summary(queryset: QuerySet[Any], academy_ids: list[int]) -> dict[str, Any]:
    by_level = {
        row["risk_level"]: row["total"] for row in queryset.values("risk_level").annotate(total=Count("id")).order_by("risk_level")
    }
    aggregates = queryset.aggregate(total=Count("id"), average_score=Avg("churn_risk_score"))

    return {
        "total": aggregates["total"] or 0,
        "average_score": float(aggregates["average_score"] or 0),
        "payment_risk_count": queryset.filter(has_payment_issues=True).count(),
        "unresolved_alert_count": ChurnAlert.objects.filter(academy_id__in=academy_ids, resolved_at__isnull=True).count(),
        "risk_levels": by_level,
    }


def _values_count(queryset: QuerySet[Any], key: str, output_key: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        queryset.exclude(**{f"{key}__isnull": True})
        .exclude(**{key: ""})
        .values(key)
        .annotate(count=Count("id"))
        .order_by("-count", key)[:limit]
    )
    return [{output_key: row[key], "count": row["count"]} for row in rows]


def _build_acquisition_summary(queryset: QuerySet[Any], academy_ids: list[int]) -> dict[str, Any]:
    by_source_type = {row["source_type"]: row["count"] for row in queryset.values("source_type").annotate(count=Count("id"))}
    by_funnel_tier = {
        str(row["funnel_tier"]): row["count"] for row in queryset.values("funnel_tier").annotate(count=Count("id"))
    }
    label_map = {
        "1": "won_or_sale",
        "2": "strong_lead",
        "3": "soft_lead",
        "4": "nurture_invite",
    }
    by_funnel_tier_label = {label_map[k]: by_funnel_tier.get(k, 0) for k in label_map}

    by_deal_status = {
        row["deal_status"]: row["count"]
        for row in queryset.exclude(deal_status__isnull=True).exclude(deal_status="").values("deal_status").annotate(count=Count("id"))
    }

    # Identity-deduped metrics to reduce cross-academy overlap distortion.
    # Identity key preference: user_id, fallback to normalized email.
    by_identity_best_tier: dict[str, int] = {}
    by_identity_academies: dict[str, set[int]] = defaultdict(set)
    for row in queryset.values("user_id", "email", "funnel_tier", "academy_id"):
        identity_key = None
        if row["user_id"]:
            identity_key = f"user:{row['user_id']}"
        else:
            email = (row.get("email") or "").strip().lower()
            if email:
                identity_key = f"email:{email}"

        if not identity_key:
            continue

        current_tier = int(row["funnel_tier"])
        if identity_key not in by_identity_best_tier:
            by_identity_best_tier[identity_key] = current_tier
        else:
            by_identity_best_tier[identity_key] = min(by_identity_best_tier[identity_key], current_tier)

        by_identity_academies[identity_key].add(int(row["academy_id"]))

    by_funnel_tier_identities = {str(tier): 0 for tier in [1, 2, 3, 4]}
    for tier in by_identity_best_tier.values():
        by_funnel_tier_identities[str(int(tier))] += 1

    by_funnel_tier_label_identities = {label_map[k]: by_funnel_tier_identities.get(k, 0) for k in label_map}
    cross_academy_identities = sum(1 for academies in by_identity_academies.values() if len(academies) > 1)

    event_slug_sources = (
        Q(source_type=AcquisitionReport.SourceType.USER_INVITE)
        | Q(source_type=AcquisitionReport.SourceType.EVENT_RSVP)
        | Q(source_type=AcquisitionReport.SourceType.EVENT_ATTENDED)
    )

    row_count = queryset.count()
    return {
        "report_row_count": row_count,
        "unique_identities": len(by_identity_best_tier),
        "cross_academy_identities": cross_academy_identities,
        "by_source_type": by_source_type,
        "by_funnel_tier": by_funnel_tier,
        "by_funnel_tier_label": by_funnel_tier_label,
        "by_funnel_tier_identities": by_funnel_tier_identities,
        "by_funnel_tier_label_identities": by_funnel_tier_label_identities,
        "top_asset_slugs": _values_count(queryset.filter(source_type=AcquisitionReport.SourceType.USER_INVITE), "asset_slug", "asset_slug"),
        "top_event_slugs": _values_count(queryset.filter(event_slug_sources), "event_slug", "event_slug"),
        "top_utm_sources": _values_count(queryset, "utm_source", "utm_source"),
        "top_utm_campaigns": _values_count(queryset, "utm_campaign", "utm_campaign"),
        "top_conversion_urls": _values_count(queryset, "conversion_url", "conversion_url"),
        "by_deal_status": by_deal_status,
        "team_seat_invite_count": queryset.filter(team_seat_invite=True).count(),
    }


REPORT_API_REGISTRY: dict[str, ReportApiConfig] = {
    "churn": ReportApiConfig(
        slug="churn",
        label="Churn Risk Report",
        description="Daily user churn risk scores and alert signals",
        model=ChurnRiskReport,
        list_serializer=ChurnRiskReportListSerializer,
        detail_serializer=ChurnRiskReportDetailSerializer,
        filters={
            "academy": {"lookup": "academy_id", "type": "int"},
            "date": {"lookup": "report_date", "type": "date"},
            "risk_level": {"lookup": "risk_level", "type": "str", "choices": [x[0] for x in ChurnRiskReport.RiskLevel.choices]},
            "user": {"lookup": "user_id", "type": "int"},
            "min_score": {"lookup": "churn_risk_score__gte", "type": "float"},
            "max_score": {"lookup": "churn_risk_score__lte", "type": "float"},
        },
        sort_fields=(
            "report_date",
            "-report_date",
            "churn_risk_score",
            "-churn_risk_score",
            "risk_level",
            "-risk_level",
            "created_at",
            "-created_at",
            "user_id",
            "-user_id",
        ),
        default_sort="-report_date",
        supports_detail=True,
        supports_summary=True,
        summary_builder=_build_churn_summary,
        date_field="report_date",
    ),
    "acquisition": ReportApiConfig(
        slug="acquisition",
        label="Acquisition Report",
        description="Daily acquisition snapshots (form leads, form wins by won_at, invites, event RSVP/attendance). FORM_ENTRY is keyed to lead creation date; FORM_ENTRY_WON to win date. Use by_source_type for splits; report_row_count is rows matching filters (not deduped identities).",
        model=AcquisitionReport,
        list_serializer=AcquisitionReportListSerializer,
        detail_serializer=AcquisitionReportDetailSerializer,
        filters={
            "academy": {"lookup": "academy_id", "type": "int"},
            "date": {"lookup": "report_date", "type": "date"},
            "date_start": {"lookup": "report_date__gte", "type": "date"},
            "date_end": {"lookup": "report_date__lte", "type": "date"},
            "source_type": {
                "lookup": "source_type",
                "type": "str",
                "choices": [x[0] for x in AcquisitionReport.SourceType.choices],
            },
            "user": {"lookup": "user_id", "type": "int"},
            "utm_source": {"lookup": "utm_source", "type": "str"},
            "utm_campaign": {"lookup": "utm_campaign", "type": "str"},
            "deal_status": {"lookup": "deal_status", "type": "str"},
            "asset_slug": {"lookup": "asset_slug", "type": "str"},
            "event_slug": {"lookup": "event_slug", "type": "str"},
            "funnel_tier": {
                "lookup": "funnel_tier",
                "type": "int",
                "choices": [x[0] for x in AcquisitionReport.FunnelTier.choices],
            },
        },
        sort_fields=(
            "report_date",
            "-report_date",
            "created_at",
            "-created_at",
            "source_type",
            "-source_type",
            "funnel_tier",
            "-funnel_tier",
            "user_id",
            "-user_id",
        ),
        default_sort="-report_date",
        supports_detail=True,
        supports_summary=True,
        summary_builder=_build_acquisition_summary,
        date_field="report_date",
    ),
}


def get_report_api_config(report_type: str) -> ReportApiConfig | None:
    return REPORT_API_REGISTRY.get(report_type)


def get_report_type_metadata() -> list[dict[str, Any]]:
    data = []
    for config in REPORT_API_REGISTRY.values():
        data.append(
            {
                "slug": config.slug,
                "label": config.label,
                "description": config.description,
                "filters": list(config.filters.keys()),
                "sort_fields": list(config.sort_fields),
                "supports_detail": config.supports_detail,
                "supports_summary": config.supports_summary,
            }
        )
    return data


def resolve_default_date(queryset: QuerySet[Any], date_field: str | None) -> date | None:
    if not date_field:
        return None

    latest = queryset.order_by(f"-{date_field}").values_list(date_field, flat=True).first()
    if latest is None:
        return None

    return latest
