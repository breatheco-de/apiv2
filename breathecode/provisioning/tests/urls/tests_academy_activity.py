"""
Test /v1/marketing/upload
"""
import csv
import json
import random
import tempfile
import os
import hashlib
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from breathecode.utils.api_view_extensions.extensions import lookup_extension
from ..mixins import ProvisioningTestCase
from breathecode.marketing.views import MIME_ALLOW
import pandas as pd
from django.utils import timezone, dateparse
from breathecode.provisioning import tasks

UTC_NOW = timezone.now()

HEADER = ','.join([
    'bill',
    'currency_code',
    'id',
    'multiplier',
    'price_per_unit',
    'processed_at',
    'product_name',
    'quantity',
    'registered_at',
    'repository_url',
    'sku',
    'status',
    'unit_type',
    'username',
])


def format_field(x):
    if x is None:
        return ''

    return str(x)


def format_csv(provisioning_activity, provisioning_bill=None):
    return ','.join([
        format_field(provisioning_bill.id if provisioning_bill else ''),
        format_field(provisioning_activity.currency_code),
        format_field(provisioning_activity.id),
        format_field(float(provisioning_activity.multiplier)),
        format_field(provisioning_activity.price_per_unit),
        format_field(provisioning_activity.processed_at),
        format_field(provisioning_activity.product_name),
        format_field(provisioning_activity.quantity),
        format_field(provisioning_activity.registered_at),
        format_field(provisioning_activity.repository_url),
        format_field(provisioning_activity.sku),
        format_field(provisioning_activity.status),
        format_field(provisioning_activity.unit_type),
        format_field(provisioning_activity.username),
    ])


def get_serializer(provisioning_activity, provisioning_bill=None):
    return {
        'bill': provisioning_bill.id if provisioning_bill else None,
        'currency_code': provisioning_activity.currency_code,
        'id': provisioning_activity.id,
        'multiplier': provisioning_activity.multiplier,
        'price_per_unit': provisioning_activity.price_per_unit,
        'processed_at': provisioning_activity.processed_at,
        'product_name': provisioning_activity.product_name,
        'quantity': provisioning_activity.quantity,
        'registered_at': provisioning_activity.registered_at,
        'repository_url': provisioning_activity.repository_url,
        'sku': provisioning_activity.sku,
        'status': provisioning_activity.status,
        'unit_type': provisioning_activity.unit_type,
        'username': provisioning_activity.username,
    }


class MarketingTestSuite(ProvisioningTestCase):
    """Test /answer"""

    # When: no auth
    # Then: should return 401
    def test_upload_without_auth(self):

        self.headers(accept='application/json', content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_activity')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no capability
    # Then: should return 403
    def test_upload_without_capability(self):

        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        self.headers(academy=1,
                     accept='application/json',
                     content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_activity')

        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_provisioning_activity for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: No activity
    # Then: Should return empty csv
    def test_no_activity(self):

        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='read_provisioning_activity')
        self.bc.request.authenticate(model.user)

        self.headers(academy=1, accept='text/csv', content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_activity')

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningActivity'), [])

    # Given: 2 ProvisioningActivity and 1 ProvisioningBill
    # When: no filters
    # Then: Should return 2 rows
    def test__csv__activities(self):

        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='read_provisioning_activity',
                                        provisioning_activity=2,
                                        provisioning_bill=1)
        self.bc.request.authenticate(model.user)

        self.headers(academy=1, accept='text/csv', content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_activity')

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = '\r\n'.join([
            HEADER,
            format_csv(model.provisioning_activity[1], model.provisioning_bill),
            format_csv(model.provisioning_activity[0], model.provisioning_bill),
            '',
        ])

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('provisioning.ProvisioningActivity'),
            self.bc.format.to_dict(model.provisioning_activity),
        )

    # Given: 2 ProvisioningActivity and 1 ProvisioningBill
    # When: no filters
    # Then: Should return 2 rows
    def test__json__activities(self):

        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='read_provisioning_activity',
                                        provisioning_activity=2,
                                        provisioning_bill=1)
        self.bc.request.authenticate(model.user)

        self.headers(academy=1,
                     accept='application/json',
                     content_disposition='attachment; filename="filename.csv"')

        url = reverse_lazy('provisioning:academy_activity')

        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(model.provisioning_activity[1], model.provisioning_bill),
            get_serializer(model.provisioning_activity[0], model.provisioning_bill),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('provisioning.ProvisioningActivity'),
            self.bc.format.to_dict(model.provisioning_activity),
        )

    # Given: compile_lookup was mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch('breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup',
           MagicMock(wraps=lookup_extension.compile_lookup))
    def test_lookup_extension(self):
        self.bc.request.set_headers(academy=1, accept='application/json')

        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='read_provisioning_activity',
                                        provisioning_activity=2,
                                        provisioning_bill=1)

        self.bc.request.authenticate(model.user)

        args, kwargs = self.bc.format.call(
            'en',
            strings={
                'exact': [
                    'hash',
                    'username',
                    'product_name',
                    'status',
                ],
            },
            datetimes={
                'gte': ['registered_at'],
                'lte': ['created_at'],  # fix it
            },
            overwrite={
                'start': 'registered_at',
                'end': 'created_at',
            },
        )

        query = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy('provisioning:academy_activity') + '?' + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], ['hash', 'username', 'product_name', 'status', 'start', 'end'])

        response = self.client.get(url)

        json = response.json()
        expected = []

        for x in ['overwrite', 'custom_fields']:
            if x in kwargs:
                del kwargs[x]

        for field in ['ids', 'slugs']:
            values = kwargs.get(field, tuple())
            kwargs[field] = tuple(values)

        for field in ['ints', 'strings', 'bools', 'datetimes']:
            modes = kwargs.get(field, {})
            for mode in modes:
                if not isinstance(kwargs[field][mode], tuple):
                    kwargs[field][mode] = tuple(kwargs[field][mode])

            kwargs[field] = frozenset(modes.items())

        self.bc.check.calls(lookup_extension.compile_lookup.call_args_list, [
            call(**kwargs),
        ])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of('provisioning.ProvisioningActivity'),
            self.bc.format.to_dict(model.provisioning_activity),
        )

    # When: get is called
    # Then: it's setup properly
    @patch.object(APIViewExtensionHandlers, '_spy_extensions', MagicMock())
    @patch.object(APIViewExtensionHandlers, '_spy_extension_arguments', MagicMock())
    def test_get__spy_extensions(self):
        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='read_provisioning_activity',
                                        provisioning_activity=2,
                                        provisioning_bill=1)

        self.bc.request.set_headers(academy=1, accept='application/json')
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('provisioning:academy_activity')
        self.client.get(url)

        self.bc.check.calls(APIViewExtensionHandlers._spy_extensions.call_args_list, [
            call(['LanguageExtension', 'LookupExtension', 'SortExtension']),
        ])

        self.bc.check.calls(APIViewExtensionHandlers._spy_extension_arguments.call_args_list, [
            call(sort='-id'),
        ])
