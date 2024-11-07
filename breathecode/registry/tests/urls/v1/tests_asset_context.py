from unittest.mock import MagicMock, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin import Breathecode
from breathecode.utils.api_view_extensions.extensions import lookup_extension

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


def get_serializer(asset_context, data={}):

    return {
        "id": asset_context.id,
        "ai_context": asset_context.ai_context,
        "category": {
            "id": asset_context.asset.id,
            "slug": asset_context.asset.slug,
            "title": asset_context.asset.title,
        },
        **data,
    }


def test_with_no_assets(bc: Breathecode, client):

    url = reverse_lazy("registry:asset_context", kwargs={"asset_id": 1})
    response = client.get(url)
    json = response.json()

    assert json == {"detail": "asset-not-found", "status_code": 404}
    assert response.status_code == 404
