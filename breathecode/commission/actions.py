from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Sum

from breathecode.activity.actions import ENGAGEMENT_POINTS
from breathecode.admissions.models import Cohort
from .models import CohortTeacherInfluencer
from breathecode.authenticate.models import ProfileAcademy
from breathecode.payments.models import Invoice
from breathecode.services.google_cloud.big_query import BigQuery


logger = logging.getLogger(__name__)


def get_teacher_influencer_academy_ids(influencer: User) -> list[int]:
    return list(
        ProfileAcademy.objects.filter(user=influencer, role__slug="teacher_influencer", status="ACTIVE").values_list(
            "academy_id", flat=True
        )
    )


def get_eligible_cohort_ids(influencer: User, academy_ids: list[int]) -> list[int]:
    cohort_ids = list(
        CohortTeacherInfluencer.objects.filter(
            influencer=influencer, is_active=True, cohort__academy_id__in=academy_ids
        ).values_list("cohort_id", flat=True)
    )

    eligible: list[int] = []

    if len(cohort_ids) > 0:

        for cohort_id in cohort_ids:
            if not cohort_id:
                continue
            if Cohort.objects.filter(id=cohort_id, micro_cohorts__isnull=False).exists():
                continue
            eligible.append(cohort_id)

    return eligible


def get_usage_invoices_excluding_referrals(start_dt: datetime, end_dt: datetime, referral_buyer_ids: set[int]):
    return (
        Invoice.objects.filter(
            status=Invoice.Status.FULFILLED,
            refunded_at__isnull=True,
            paid_at__gte=start_dt,
            paid_at__lt=end_dt,
            payment_method__is_backed=True,
        )
        .select_related("bag", "currency", "academy", "user", "payment_method")
        .exclude(user_id__in=referral_buyer_ids)
    )


def filter_invoices_by_plans_and_cohorts(
    invoices, include_plans: str = None, exclude_plans: str = None, eligible_cohort_ids: list[int] = None
):
    """
    Filter invoices based on plans and cohort relationships.

    Args:
        invoices: QuerySet of invoices to filter
        include_plans: comma-separated plan slugs to include
        exclude_plans: comma-separated plan slugs to exclude
        eligible_cohort_ids: list of cohort IDs where influencer is active

    Returns:
        Filtered QuerySet of invoices
    """
    initial_count = invoices.count()
    logger.info(f"Initial invoices count: {initial_count}")

    filtered_invoices = invoices

    if include_plans:
        plan_slugs = [slug.strip() for slug in include_plans.split(",") if slug.strip()]
        filtered_invoices = filtered_invoices.filter(bag__plans__slug__in=plan_slugs)
        logger.info(f"After including plans {plan_slugs}: {filtered_invoices.count()} invoices")

    if exclude_plans:
        plan_slugs = [slug.strip() for slug in exclude_plans.split(",") if slug.strip()]
        filtered_invoices = filtered_invoices.exclude(bag__plans__slug__in=plan_slugs)
        logger.info(f"After excluding plans {plan_slugs}: {filtered_invoices.count()} invoices")

    if not include_plans and not exclude_plans and eligible_cohort_ids:
        from breathecode.payments.models import CohortSet, Plan

        cohort_sets = CohortSet.objects.filter(cohorts__id__in=eligible_cohort_ids).distinct()
        related_plans = Plan.objects.filter(cohort_set__in=cohort_sets).distinct()

        logger.info(f"Found {cohort_sets.count()} cohort sets for {len(eligible_cohort_ids)} eligible cohorts")
        logger.info(f"Found {related_plans.count()} related plans")

        if related_plans.exists():
            filtered_invoices = filtered_invoices.filter(bag__plans__in=related_plans)
            logger.info(f"After filtering by cohort-related plans: {filtered_invoices.count()} invoices")

    return filtered_invoices.distinct()


def compute_usage_rows_and_total(
    influencer: User,
    start_dt: datetime,
    end_dt: datetime,
    usage_invoices,
    eligible_cohort_ids: list[int],
) -> tuple[list[dict[str, Any]], float, dict[int, dict[int, dict[str, float]]]]:
    rows: list[dict[str, Any]] = []
    total = 0.0
    user_breakdown_by_cohort: dict[int, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))

    candidate_user_ids = list(usage_invoices.values_list("user_id", flat=True).distinct())

    if not candidate_user_ids or not eligible_cohort_ids:
        return rows, total, user_breakdown_by_cohort

    try:
        client, project_id, dataset = BigQuery.client()
    except Exception as e:
        logger.warning(f"BigQuery not available: {e}. Skipping usage commission calculation.")
        return rows, total, user_breakdown_by_cohort

    allowed = [(rt, k) for (rt, k), v in ENGAGEMENT_POINTS.items() if v > 0]
    task_kinds = [kind for (_, kind) in allowed]
    related_types = list({related_type for (related_type, _) in allowed})

    kinds_in = ",".join([f"'{k}'" for k in task_kinds]) if task_kinds else "''"
    rtypes_in = ",".join([f"'{t}'" for t in related_types]) if related_types else "''"

    user_ids_in = ",".join(str(x) for x in set(candidate_user_ids))

    sql = f"""
        WITH task_events AS (
          SELECT
            CAST(user_id AS INT64) AS user_id,
            related.type AS related_type,
            CAST(related.id AS INT64) AS related_id,
            kind,
            SAFE_CAST(meta.cohort AS INT64) AS cohort_id,
            TIMESTAMP(timestamp) AS ts
          FROM `{project_id}.{dataset}.activity`
          WHERE related.type IN ({rtypes_in})
            AND TIMESTAMP(timestamp) >= TIMESTAMP('{start_dt.isoformat()}')
            AND TIMESTAMP(timestamp) <  TIMESTAMP('{end_dt.isoformat()}')
            AND user_id IN ({user_ids_in})
            AND kind IN ({kinds_in})
        )
        SELECT AS VALUE ARRAY_AGG(t ORDER BY ts ASC LIMIT 1)[OFFSET(0)]
        FROM task_events t
        WHERE cohort_id IS NOT NULL
        GROUP BY user_id, related_id, kind
    """

    try:
        bq_rows = list(client.query(sql).result())
        logger.info(f"BigQuery returned {len(bq_rows)} rows")

    except Exception:
        logger.warning("BigQuery query failed. Skipping usage commission calculation.")
        return rows, total, user_breakdown_by_cohort

    user_total_points: dict[int, float] = defaultdict(float)
    user_cohort_points: dict[int, dict[int, float]] = defaultdict(dict)

    for r in bq_rows:
        try:
            user_id = int(r[0]) if len(r) > 0 else 0
            related_type = str(r[1]) if len(r) > 1 else ""
            kind = str(r[3]) if len(r) > 3 else ""
            cohort_id = int(r[4]) if len(r) > 4 else 0

        except Exception:
            continue

        if user_id <= 0 or not related_type or not kind or cohort_id <= 0:
            continue

        pts = ENGAGEMENT_POINTS.get((related_type, kind), 0.0)
        if pts <= 0:
            continue

        user_total_points[user_id] += pts
        if cohort_id in eligible_cohort_ids:
            user_cohort_points.setdefault(user_id, {})[cohort_id] = (
                user_cohort_points.get(user_id, {}).get(cohort_id, 0.0) + pts
            )

        # Track breakdown by user and cohort
        user_breakdown_by_cohort[user_id][cohort_id][kind] = (
            user_breakdown_by_cohort[user_id][cohort_id].get(kind, 0.0) + pts
        )

    paid_by_user_currency = (
        usage_invoices.values("user_id", "currency_id")
        .annotate(total_amount=Sum("amount"))
        .values_list("user_id", "currency_id", "total_amount")
    )

    currency_map = {inv.currency_id: inv.currency.code for inv in usage_invoices}

    for user_id, currency_id, total_amount in paid_by_user_currency:
        total_amount = float(total_amount or 0)
        if total_amount <= 0:
            continue
        if user_id not in user_total_points:
            continue

        total_pts = user_total_points.get(user_id, 0.0)
        if total_pts <= 0:
            continue

        pool = round(total_amount * 0.3, 2)
        cohort_points = user_cohort_points.get(user_id, {})
        inf_pts = sum(cohort_points.values())
        if inf_pts <= 0:
            continue

        for cid, pts in cohort_points.items():
            cohort_commission = pool * (pts / total_pts)
            rows.append(
                {
                    "type": "usage",
                    "user_id": user_id,
                    "cohort_id": cid,
                    "currency": currency_map.get(currency_id, ""),
                    "paid_amount": round(total_amount, 2),
                    "total_points": round(total_pts, 2),
                    "cohort_points": round(pts, 2),
                    "commission": round(cohort_commission, 2),
                }
            )
            total += round(cohort_commission, 2)

    return rows, total, user_breakdown_by_cohort
