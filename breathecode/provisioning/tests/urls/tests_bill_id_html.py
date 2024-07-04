"""
Test cases for /academy/:id/member/:id
"""

import os

from django.template import loader
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
    }


def provisioning_bill_serializer(provisioning_bill, academy):
    return {
        "id": provisioning_bill.id,
        "total_amount": provisioning_bill.total_amount,
        "academy": academy_serializer(academy),
        "status": provisioning_bill.status,
        "paid_at": provisioning_bill.paid_at,
        "stripe_url": provisioning_bill.stripe_url,
        "created_at": provisioning_bill.created_at,
    }


def provisioning_consumption_kind_serializer(provisioning_consumption_kind):
    return {
        "product_name": provisioning_consumption_kind.product_name,
        "sku": provisioning_consumption_kind.sku,
    }


def provisioning_user_consumption_serializer(
    provisioning_user_consumption, provisioning_consumption_kind, provisioning_price, provisioning_consumption_events=[]
):

    quantity = 0
    price = 0
    prices = []

    for event in provisioning_consumption_events:
        quantity += event.quantity
        p = event.quantity * provisioning_price.price_per_unit * provisioning_price.multiplier
        price += p
        prices.append({"price": p, "price_per_unit": provisioning_price.price_per_unit, "quantity": event.quantity})

    resume = ""

    for p in prices:
        resume += f'{p["quantity"]} x {p["price_per_unit"]} = {p["price"]}\n'

    return {
        "username": provisioning_user_consumption.username,
        "status": provisioning_user_consumption.status,
        "amount": float(provisioning_user_consumption.amount),
        "status_text": provisioning_user_consumption.status_text,
        "kind": provisioning_consumption_kind_serializer(provisioning_consumption_kind),
        "price_description": (quantity, price, resume),
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_successfully(
    provisioning_bill=None,
    token=None,
    academy=None,
    provisioning_consumption_kind=None,
    provisioning_price=None,
    provisioning_user_consumptions=[],
    provisioning_consumption_events=[],
    data={},
):
    request = None
    APP_URL = os.getenv("APP_URL", "")

    template = loader.get_template("provisioning_invoice.html")
    status_map = {
        "DUE": "Due",
        "DISPUTED": "Disputed",
        "IGNORED": "Ignored",
        "PENDING": "Pending",
        "PAID": "Paid",
        "ERROR": "Error",
    }

    total_price = 0
    for bill in []:
        total_price += bill["total_price"]

    status = data.get("status", "DUE")

    provisioning_user_consumptions = sorted(provisioning_user_consumptions, key=lambda x: x.username)

    data = {
        "API_URL": None,
        "COMPANY_NAME": "",
        "COMPANY_CONTACT_URL": "",
        "COMPANY_LEGAL_NAME": "",
        "COMPANY_ADDRESS": "",
        "style__success": "#99ccff",
        "style__danger": "#ffcccc",
        "style__secondary": "#ededed",
        "status": status,
        "token": token.key,
        "title": f"Payments {status_map[status]}",
        "possible_status": [(key, status_map[key]) for key in status_map],
        "bills": provisioning_bill,
        "total_price": total_price,
        **data,
        "bill": provisioning_bill_serializer(provisioning_bill, academy),
        "consumptions": [
            provisioning_user_consumption_serializer(
                provisioning_user_consumption,
                provisioning_consumption_kind,
                provisioning_price,
                provisioning_consumption_events=provisioning_consumption_events,
            )
            for provisioning_user_consumption in provisioning_user_consumptions
        ],
        "status": status_map[provisioning_bill.status],
        "title": academy.name,
        "url": f"/v1/provisioning/bill/{provisioning_bill.id}/html?token={token.key}",
    }

    if academy:
        data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        data["COMPANY_LOGO"] = academy.logo_url
        data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            data["heading"] = academy.name

    return template.render(data)


def render(message):
    request = None
    return loader.render_to_string(
        "message.html",
        {"MESSAGE": message, "BUTTON": None, "BUTTON_TARGET": "_blank", "LINK": None},
        request,
        using=None,
    )


class AuthenticateTestSuite(ProvisioningTestCase):
    # When: no auth
    # Then: return 302
    def test_without_auth(self):
        url = reverse_lazy("provisioning:bill_id_html", kwargs={"id": 1})
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/v1/provisioning/bill/1/html")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])

    # When: no profile academies
    # Then: return 403
    def test_403(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("provisioning:bill_id_html", kwargs={"id": 1}) + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render("no-access")

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])

    # When: 1 bill and 2 activities
    # Then: return 200
    def test_2_activities(self):
        model = self.bc.database.create(
            user=1,
            token=1,
            provisioning_bill=1,
            provisioning_user_consumption=2,
            provisioning_consumption_event=2,
            profile_academy=1,
            academy=1,
            role=1,
            capability="crud_provisioning_bill",
        )

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("provisioning:bill_id_html", kwargs={"id": 1}) + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_successfully(
            provisioning_bill=model.provisioning_bill,
            token=model.token,
            academy=model.academy,
            provisioning_consumption_kind=model.provisioning_consumption_kind,
            provisioning_price=model.provisioning_price,
            provisioning_user_consumptions=model.provisioning_user_consumption,
            provisioning_consumption_events=model.provisioning_consumption_event,
            data={
                "pages": 1,
                "page": 1,
            },
        )

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("provisioning.ProvisioningBill"),
            [
                self.bc.format.to_dict(model.provisioning_bill),
            ],
        )
