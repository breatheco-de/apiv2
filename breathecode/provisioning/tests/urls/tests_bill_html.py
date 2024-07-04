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


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_successfully(provisioning_bills=[], token=None, data={}):
    request = None
    APP_URL = os.getenv("APP_URL", "")

    template = loader.get_template("provisioning_bills.html")
    status_mapper = {
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
        "title": f"Payments {status_mapper[status]}",
        "possible_status": [(key, status_mapper[key]) for key in status_mapper],
        "bills": provisioning_bills,
        "total_price": total_price,
        **data,
    }

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
        url = reverse_lazy("provisioning:bill_html")
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/v1/provisioning/bill/html")
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
        url = reverse_lazy("provisioning:bill_html") + f"?{querystring}"
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

    # When: 2 bills
    # Then: return 200
    def test_2_bills(self):
        profile_academies = [{"academy_id": n + 1} for n in range(2)]
        provisioning_bills = [{"academy_id": n + 1} for n in range(2)]
        model = self.bc.database.create(
            user=1,
            token=1,
            provisioning_bill=provisioning_bills,
            profile_academy=profile_academies,
            academy=2,
            role=1,
            capability="read_provisioning_bill",
        )

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("provisioning:bill_html") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_successfully(provisioning_bills=model.provisioning_bill, token=model.token, data={})
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
            self.bc.format.to_dict(model.provisioning_bill),
        )

    # When: 2 bills, just show the bills belong to one academy
    # Then: return 200
    def test_2_bills__just_show_one_academy(self):
        profile_academies = [{"academy_id": n + 1} for n in range(2)]
        provisioning_bills = [{"academy_id": n + 1} for n in range(2)]
        model = self.bc.database.create(
            user=1,
            token=1,
            provisioning_bill=provisioning_bills,
            profile_academy=profile_academies,
            academy=2,
            role=1,
            capability="read_provisioning_bill",
        )

        querystring = self.bc.format.to_querystring({"token": model.token.key, "academy": 1})
        url = reverse_lazy("provisioning:bill_html") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_successfully(provisioning_bills=[model.provisioning_bill[0]], token=model.token, data={})
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
            self.bc.format.to_dict(model.provisioning_bill),
        )
