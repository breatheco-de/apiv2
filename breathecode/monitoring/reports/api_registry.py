from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from django.db.models import Avg, Count, Model, QuerySet

from breathecode.monitoring.reports.churn.models import ChurnAlert, ChurnRiskReport
from breathecode.monitoring.serializers import ChurnRiskReportDetailSerializer, ChurnRiskReportListSerializer

SummaryBuilder = Callable[[QuerySet[Any], int], dict[str, Any]]


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


def _build_churn_summary(queryset: QuerySet[Any], academy_id: int) -> dict[str, Any]:
    by_level = {
        row["risk_level"]: row["total"] for row in queryset.values("risk_level").annotate(total=Count("id")).order_by("risk_level")
    }
    aggregates = queryset.aggregate(total=Count("id"), average_score=Avg("churn_risk_score"))

    return {
        "total": aggregates["total"] or 0,
        "average_score": float(aggregates["average_score"] or 0),
        "payment_risk_count": queryset.filter(has_payment_issues=True).count(),
        "unresolved_alert_count": ChurnAlert.objects.filter(academy_id=academy_id, resolved_at__isnull=True).count(),
        "risk_levels": by_level,
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
