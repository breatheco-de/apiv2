from unittest.mock import MagicMock, call, patch

from django.urls import reverse_lazy
from rest_framework import status

from breathecode.utils.api_view_extensions.extensions import lookup_extension
from ..mixins import PaymentsTestCase


def academy_serializer(academy):
    return {
        "id": academy.id,
        "name": academy.name,
        "slug": academy.slug,
    }


def event_type_serializer(event_type, academy):
    return {
        # 'academy': academy_serializer(academy),
        "description": event_type.description,
        "lang": event_type.lang,
        "name": event_type.name,
        "id": event_type.id,
        "slug": event_type.slug,
        "icon_url": event_type.icon_url,
        "allow_shared_creation": event_type.allow_shared_creation,
    }


def get_serializer(event_type_set, event_types, academy):
    return {
        "id": event_type_set.id,
        "slug": event_type_set.slug,
        "academy": academy_serializer(academy),
        "event_types": [event_type_serializer(event_type, academy) for event_type in event_types],
    }


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    # Given: 0 EventTypeSet
    # When: get with no auth
    # Then: return 200
    def test__no_auth(self):
        url = reverse_lazy("payments:eventtypeset")
        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("payments.EventTypeSet"), [])

    # Given: 2 EventTypeSet, 2 MentorshipService and 1 Academy
    # When: get with no auth
    # Then: return 200 with 2 EventTypeSet
    def test__two_items(self):
        event_types = [{"icon_url": self.bc.fake.url()} for _ in range(2)]
        model = self.bc.database.create(event_type_set=2, event_type=event_types)

        url = reverse_lazy("payments:eventtypeset")
        response = self.client.get(url)

        json = response.json()
        expected = [
            get_serializer(
                model.event_type_set[1],
                [model.event_type[0], model.event_type[1]],
                model.academy,
            ),
            get_serializer(
                model.event_type_set[0],
                [model.event_type[0], model.event_type[1]],
                model.academy,
            ),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("payments.EventTypeSet"),
            self.bc.format.to_dict(model.event_type_set),
        )

    # Given: compile_lookup was mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch(
        "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
        MagicMock(wraps=lookup_extension.compile_lookup),
    )
    def test_lookup_extension(self):
        self.bc.request.set_headers(academy=1)

        event_types = [{"icon_url": self.bc.fake.url()} for _ in range(2)]
        model = self.bc.database.create(event_type_set=2, event_type=event_types)

        args, kwargs = self.bc.format.call(
            "en",
            strings={"exact": ["event_types__lang"]},
            slugs=[
                "",
                "academy",
                "event_types",
            ],
            overwrite={
                "event_type": "event_types",
                "lang": "event_types__lang",
            },
        )

        query = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy("payments:eventtypeset") + "?" + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], ["id", "slug", "academy", "event_type", "lang"])

        response = self.client.get(url)

        json = response.json()
        expected = []

        for x in ["overwrite", "custom_fields"]:
            if x in kwargs:
                del kwargs[x]

        for field in ["ids", "slugs"]:
            values = kwargs.get(field, tuple())
            kwargs[field] = tuple(values)

        for field in ["ints", "strings", "bools", "datetimes"]:
            modes = kwargs.get(field, {})
            for mode in modes:
                if not isinstance(kwargs[field][mode], tuple):
                    kwargs[field][mode] = tuple(kwargs[field][mode])

            kwargs[field] = frozenset(modes.items())

        self.bc.check.calls(
            lookup_extension.compile_lookup.call_args_list,
            [
                call(**kwargs),
            ],
        )

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.bc.database.list_of("payments.EventTypeSet"),
            self.bc.format.to_dict(model.event_type_set),
        )
