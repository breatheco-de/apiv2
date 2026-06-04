---
name: ""
overview: ""
todos: []
isProject: false
---

# Addendum: Vendor service scopes (vps_server, coding_environment)

This extends the "VPS provisioning API-only config" work with vendor service scopes and validation.

---

## 1. Model: ProvisioningVendor.services

**File:** [breathecode/provisioning/models.py](breathecode/provisioning/models.py)

- Add field: `services = models.JSONField(default=list, blank=True, help_text="List of service slugs this vendor provides, e.g. vps_server, coding_environment")`.
- Store a list of strings, e.g. `["vps_server"]` or `["vps_server", "coding_environment"]`.
- Add constants (on the model or in a small `provisioning/constants.py`) so the rest of the app uses the same slugs:
  - `VendorService.VPS_SERVER = "vps_server"`
  - `VendorService.CODING_ENVIRONMENT = "coding_environment"`
  - Optional: `VendorService.ALL = (VPS_SERVER, CODING_ENVIRONMENT)` and a validator that only allows these values.

**Migration:** New migration adding `services` (default=[]). Optionally a data migration to set existing vendors (e.g. Hostinger → `["vps_server"]`, Gitpod/Codespaces → `["coding_environment"]`) if you have known mappings.

---

## 2. List vendors: filter by `service` querystring

**GET /v1/provisioning/academy/vendor** (or wherever the vendor list lives)

- Querystring: `service=vps_server` or `service=vps_server,coding_environment` (comma-separated).
- Semantics: return vendors that offer **all** requested services (AND). So `?service=vps_server,coding_environment` → vendors whose `services` list contains both.
- Implementation: parse `request.GET.get("service", "")` into a list of slugs (strip, skip empty). For each slug, filter: `qs = qs.filter(services__contains=[slug])`. PostgreSQL JSONField supports `__contains` for list containment.
- If `service` is empty or not sent, return all vendors (no filter on services).

---

## 3. Validation: “vendor must offer the service”

**Requirement:** When a vendor is used for a specific purpose (e.g. VPS provisioning uses `vps_server`), the vendor must have that service in `services`. Otherwise it must not be used for that purpose.

**Recommendation: do not use a decorator.** Use a **model method + explicit checks** at use-sites.

**Why not a decorator?**

- The “vendor” is usually not a direct argument of the view or action. In `get_eligible_academy_and_vendor_for_vps` we loop over profiles and resolve the vendor inside the loop; there is no single “vendor” argument to pass into a decorator.
- Validation happens in different places: when **selecting** a vendor (e.g. in `get_eligible_academy_and_vendor_for_vps`), and when **creating/updating** config that ties an academy to a vendor (e.g. ProvisioningAcademy create/update). A decorator would have to be applied to functions that receive (user) or (academy_id, vendor_id, …), and the decorator would need to load the vendor and check services—which is the same as an explicit check, but less clear.

**Preferred approach**

1. **Model method on ProvisioningVendor**
  - `def offers_service(self, service: str) -> bool`
  - Return `service in (self.services or [])`.
  - Reusable and easy to test.
2. **Use at “use” sites**
  - **get_eligible_academy_and_vendor_for_vps** ([actions.py](breathecode/provisioning/actions.py)): in the loop over profiles, after `get_vps_client(profile.vendor)` and before checking ProvisioningAcademy, add: `if not profile.vendor.offers_service("vps_server"): continue`. So we only consider vendors that offer `vps_server`.
  - **ProvisioningAcademy create/update (API):** in the serializer’s `validate()` or in the view, when saving a ProvisioningAcademy for VPS (which is the current use case), validate that `vendor.offers_service("vps_server")`. If not, raise ValidationException (e.g. “This vendor does not offer VPS provisioning”). That way staff cannot attach a coding-environment-only vendor as the VPS academy config.
3. **Optional helper** (if you want a single place that raises)
  - `require_vendor_offers_service(vendor, service, lang=None)` in actions or utils: if not `vendor.offers_service(service)`, raise ValidationException with translation. Call it from the ProvisioningAcademy serializer or from `get_eligible_academy_and_vendor_for_vps` instead of a bare `continue`, if you want a clear error when no vendor is found because none offer the service (you already raise “academy-vps-not-configured”; the current message is still correct).

**Summary:** Add `ProvisioningVendor.offers_service(service)`. Use it explicitly in the VPS resolution loop and in ProvisioningAcademy create/update. No decorator.

---

## 4. Serializer / admin

- **Vendor list serializer:** Include `services` in the response so the frontend can show which services each vendor offers.
- **Vendor create/update (if you add them):** Accept `services` as a list of strings; validate each value is in `VendorService.ALL` (or the chosen set of allowed slugs).
- **Django Admin:** Add `services` to ProvisioningVendor list_display and to the form (e.g. a comma-separated input or a multi-select backed by the same allowed slugs).

---

## 5. Backfill and tests

- Backfill existing vendors in a data migration or manually (Hostinger → `["vps_server"]`, etc.).
- Tests: list vendors with `?service=vps_server` returns only vendors with vps_server in services; list with `?service=vps_server,coding_environment` returns only vendors with both; `offers_service` returns True/False as expected; get_eligible_academy_and_vendor_for_vps skips vendors that don’t offer vps_server; ProvisioningAcademy create with a vendor that doesn’t offer vps_server returns 400 with a clear message.
