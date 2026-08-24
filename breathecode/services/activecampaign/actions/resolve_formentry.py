from django.utils import timezone

AC_DEAL_STATUS = {
    "Won": "WON",
    "Lost": "LOST",
    "0": None,
    "1": "WON",
    "2": "LOST",
}


def _payload_course(payload: dict):
    for key in ("deal[course]", "contact[course]", "course"):
        value = payload.get(key)
        if value:
            return value
    return None


def find_formentry_for_deal_payload(payload: dict, *, persisted_only: bool = True):
    """Resolve FormEntry for an AC deal webhook without stealing another deal's row."""
    from breathecode.marketing.models import FormEntry

    deal_id = payload.get("deal[id]")
    contact_id = payload.get("deal[contactid]") or payload.get("contact[id]")
    email = payload.get("deal[contact_email]") or payload.get("contact[email]")
    course = _payload_course(payload)

    persisted = ["PERSISTED"] if persisted_only else None
    persisted_or_manual = ["PERSISTED", "MANUALLY_PERSISTED"] if persisted_only else None

    def apply_storage(qs, statuses):
        if statuses is None:
            return qs
        return qs.filter(storage_status__in=statuses)

    if deal_id:
        qs = apply_storage(FormEntry.objects.filter(ac_deal_id=deal_id), persisted)
        entry = qs.order_by("-created_at").first()
        if entry is not None:
            return entry

    unbound = FormEntry.objects.filter(ac_deal_id__isnull=True)
    if course:
        unbound_course = unbound.filter(course=course)
    else:
        unbound_course = unbound

    if contact_id:
        qs = apply_storage(unbound_course.filter(ac_contact_id=contact_id), persisted)
        entry = qs.order_by("-created_at").first()
        if entry is None and course:
            qs = apply_storage(unbound.filter(ac_contact_id=contact_id), persisted)
            entry = qs.order_by("-created_at").first()
        if entry is not None:
            return entry

    if email:
        qs = apply_storage(unbound_course.filter(email=email), persisted_or_manual)
        entry = qs.order_by("-created_at").first()
        if entry is None and course:
            qs = apply_storage(unbound.filter(email=email), persisted_or_manual)
            entry = qs.order_by("-created_at").first()
        if entry is not None:
            return entry

    return None


def apply_deal_owner_and_amount(entry, payload: dict):
    if "deal[owner]" in payload:
        entry.ac_deal_owner_id = payload["deal[owner]"]
    first = payload.get("deal[owner_firstname]") or ""
    last = payload.get("deal[owner_lastname]") or ""
    if first or last:
        entry.ac_deal_owner_full_name = f"{first} {last}".strip()
    if "deal[value_raw]" in payload:
        entry.ac_deal_amount = float(payload["deal[value_raw]"])
    if "deal[currency]" in payload:
        entry.ac_deal_currency_code = payload["deal[currency]"]


def apply_deal_status_if_changed(entry, payload: dict):
    """Update deal_status only when it actually changes. Same value is a no-op for the signal."""
    if "deal[status]" not in payload or payload["deal[status]"] not in AC_DEAL_STATUS:
        return

    incoming = AC_DEAL_STATUS[payload["deal[status]"]]
    if entry.deal_status == incoming:
        return

    if entry.deal_status is None and incoming == "WON":
        entry.won_at = timezone.now()
    elif incoming != "WON":
        entry.won_at = None

    entry.deal_status = incoming


def bind_deal_to_locked_entry(locked, payload: dict):
    """Bind deal id / contact / status onto a FormEntry already locked with select_for_update."""
    deal_id = str(payload["deal[id]"])
    if locked.ac_deal_id and str(locked.ac_deal_id) != deal_id:
        raise Exception(
            f"FormEntry {locked.id} already bound to deal {locked.ac_deal_id}, "
            f"refusing to attach deal {deal_id}"
        )

    locked.ac_deal_id = deal_id
    contact_id = payload.get("deal[contactid]") or payload.get("contact[id]")
    if contact_id:
        locked.ac_contact_id = contact_id

    apply_deal_status_if_changed(locked, payload)
    apply_deal_owner_and_amount(locked, payload)
    return locked
