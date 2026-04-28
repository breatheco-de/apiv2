"""Acquisition report generation logic."""

from typing import Any

from breathecode.authenticate.models import UserInvite
from breathecode.marketing.models import FormEntry

from ..base import BaseReport
from .models import AcquisitionReport


def _is_sale_conversion(conversion_info: Any) -> bool:
    if not isinstance(conversion_info, dict):
        return False

    sale = conversion_info.get("sale")
    return isinstance(sale, dict) and len(sale) > 0


def resolve_academy_for_form_entry(entry: FormEntry, alias_lookup: dict[str, int]) -> int | None:
    if entry.academy_id:
        return entry.academy_id

    location = (entry.location or "").strip()
    if not location:
        return None

    return alias_lookup.get(location)


def resolve_academy_for_user_invite(invite: UserInvite) -> int | None:
    if invite.academy_id:
        return invite.academy_id

    if invite.cohort and invite.cohort.academy_id:
        return invite.cohort.academy_id

    if invite.course and invite.course.academy_id:
        return invite.course.academy_id

    if invite.syllabus and invite.syllabus.academy_owner_id:
        return invite.syllabus.academy_owner_id

    return None


def _get_formentry_funnel_tier(entry: FormEntry) -> int:
    if entry.deal_status == "WON":
        return AcquisitionReport.FunnelTier.WON_OR_SALE

    if entry.lead_type == "STRONG":
        return AcquisitionReport.FunnelTier.STRONG_LEAD

    if entry.lead_type == "SOFT":
        return AcquisitionReport.FunnelTier.SOFT_LEAD

    return AcquisitionReport.FunnelTier.NURTURE_INVITE


def _get_userinvite_funnel_tier(invite: UserInvite) -> int:
    if _is_sale_conversion(invite.conversion_info):
        return AcquisitionReport.FunnelTier.WON_OR_SALE

    return AcquisitionReport.FunnelTier.NURTURE_INVITE


class AcquisitionReportGenerator(BaseReport):
    """Build daily acquisition snapshots from FormEntry and UserInvite."""

    report_type = "acquisition"

    def fetch_data(self) -> dict[str, Any]:
        form_entries = list(
            FormEntry.objects.filter(created_at__date=self.report_date).select_related("academy", "user")
        )
        invites = list(
            UserInvite.objects.filter(created_at__date=self.report_date).select_related(
                "academy",
                "cohort__academy",
                "course__academy",
                "syllabus__academy_owner",
                "role",
                "author",
                "user",
                "subscription_seat",
                "plan_financing_seat",
                "payment_method",
            )
        )

        locations = {x.location.strip() for x in form_entries if x.location and x.location.strip()}
        alias_lookup = {}
        if locations:
            from breathecode.marketing.models import AcademyAlias

            alias_lookup = dict(
                AcademyAlias.objects.filter(slug__in=locations).values_list("slug", "academy_id")
            )

        return {
            "form_entries": form_entries,
            "invites": invites,
            "event_ids": [x.id for x in form_entries] + [x.id for x in invites],
            "alias_lookup": alias_lookup,
        }

    def generate(self) -> int:
        self.log(f"Starting {self.report_type} report for {self.report_date}")

        raw_data = self.fetch_data()
        form_count = len(raw_data.get("form_entries", []))
        invite_count = len(raw_data.get("invites", []))
        self.log(f"Fetched {form_count} form entries and {invite_count} invites")

        reports = self.process_data(raw_data)
        self.log(f"Processed {len(reports)} reports")

        count = self.save_reports(reports)
        self.log(f"Saved {count} reports")

        return count

    def process_data(self, raw_data: dict[str, Any]) -> list[AcquisitionReport]:
        reports: list[AcquisitionReport] = []
        alias_lookup: dict[str, int] = raw_data.get("alias_lookup", {})

        for entry in raw_data["form_entries"]:
            academy_id = resolve_academy_for_form_entry(entry, alias_lookup)
            if academy_id is None:
                continue

            if self.academy_id and academy_id != self.academy_id:
                continue

            details = {
                "source": "form_entry",
                "custom_fields": entry.custom_fields or {},
                "current_download": entry.current_download,
                "gclid": entry.gclid,
                "referral_key": entry.referral_key,
            }

            conversion_url = None
            if isinstance(entry.custom_fields, dict):
                conversion_url = entry.custom_fields.get("conversion_url")

            reports.append(
                AcquisitionReport(
                    source_type=AcquisitionReport.SourceType.FORM_ENTRY,
                    source_id=entry.id,
                    report_date=self.report_date,
                    academy_id=academy_id,
                    user_id=entry.user_id,
                    email=(entry.email or "").strip().lower(),
                    funnel_tier=_get_formentry_funnel_tier(entry),
                    utm_source=entry.utm_source,
                    utm_medium=entry.utm_medium,
                    utm_campaign=entry.utm_campaign,
                    utm_term=entry.utm_term,
                    utm_content=entry.utm_content,
                    utm_placement=entry.utm_placement,
                    landing_url=entry.utm_url,
                    conversion_url=conversion_url,
                    lead_type=entry.lead_type,
                    deal_status=entry.deal_status,
                    attribution_id=entry.attribution_id,
                    details=details,
                    team_seat_invite=False,
                )
            )

        for invite in raw_data["invites"]:
            academy_id = resolve_academy_for_user_invite(invite)
            if academy_id is None:
                continue

            if self.academy_id and academy_id != self.academy_id:
                continue

            conversion_info = invite.conversion_info if isinstance(invite.conversion_info, dict) else {}
            team_seat_invite = bool(invite.subscription_seat_id or invite.plan_financing_seat_id)
            reports.append(
                AcquisitionReport(
                    source_type=AcquisitionReport.SourceType.USER_INVITE,
                    source_id=invite.id,
                    report_date=self.report_date,
                    academy_id=academy_id,
                    user_id=invite.user_id,
                    email=(invite.email or "").strip().lower(),
                    funnel_tier=_get_userinvite_funnel_tier(invite),
                    utm_source=conversion_info.get("utm_source"),
                    utm_medium=conversion_info.get("utm_medium"),
                    utm_campaign=conversion_info.get("utm_campaign"),
                    utm_term=conversion_info.get("utm_term"),
                    utm_content=conversion_info.get("utm_content"),
                    utm_placement=conversion_info.get("utm_placement"),
                    landing_url=conversion_info.get("landing_url"),
                    conversion_url=conversion_info.get("conversion_url"),
                    event_slug=invite.event_slug,
                    asset_slug=invite.asset_slug,
                    course_id=invite.course_id,
                    cohort_id=invite.cohort_id,
                    syllabus_id=invite.syllabus_id,
                    role_id=invite.role_id,
                    author_id=invite.author_id,
                    subscription_seat_id=invite.subscription_seat_id,
                    plan_financing_seat_id=invite.plan_financing_seat_id,
                    payment_method_id=invite.payment_method_id,
                    team_seat_invite=team_seat_invite,
                    details={
                        "source": "user_invite",
                        "conversion_info": conversion_info,
                        "status": invite.status,
                        "process_status": invite.process_status,
                        "sent_at": invite.sent_at.isoformat() if invite.sent_at else None,
                        "opened_at": invite.opened_at.isoformat() if invite.opened_at else None,
                        "clicked_at": invite.clicked_at.isoformat() if invite.clicked_at else None,
                    },
                )
            )

        return reports

    def save_reports(self, reports: list[AcquisitionReport]) -> int:
        if not reports:
            return 0

        AcquisitionReport.objects.bulk_create(
            reports,
            update_conflicts=True,
            unique_fields=["source_type", "source_id"],
            update_fields=[
                "report_date",
                "academy",
                "user",
                "email",
                "funnel_tier",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "utm_placement",
                "landing_url",
                "conversion_url",
                "lead_type",
                "deal_status",
                "attribution_id",
                "event_slug",
                "asset_slug",
                "course",
                "cohort",
                "syllabus",
                "role",
                "author",
                "subscription_seat",
                "plan_financing_seat",
                "payment_method",
                "team_seat_invite",
                "details",
            ],
        )

        return len(reports)
