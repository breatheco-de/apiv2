"""
Test /answer
"""

import capyc.pytest as capy
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

UTC_NOW = timezone.now()


def test_list_op_types(client: capy.Client):
    url = reverse_lazy("v2:media:operationtype")

    response = client.get(url)

    json = response.json()
    expected = [
        "media",
        "proof-of-payment",
        "profile-picture",
    ]

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
