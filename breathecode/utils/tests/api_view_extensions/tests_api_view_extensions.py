import json
import urllib.parse
from unittest.mock import MagicMock, call, patch

import brotli
import serpy
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from breathecode.admissions.caches import CohortCache
from breathecode.admissions.models import Cohort
from breathecode.utils import APIViewExtensions
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from capyc.rest_framework.exceptions import ValidationException

from ..mixins import UtilsTestCase

cohort_cache = CohortCache()


def serialize_cache_object(data, headers={}):
    res = {
        "headers": {
            "Content-Type": "application/json",
            **headers,
        },
        "content": json.dumps(data).encode("utf-8"),
    }
    return res


def assert_pagination(headers: dict, limit, offset, lenght):
    assert "Link" in headers
    assert "X-Total-Count" in headers
    assert "X-Page" in headers
    assert "X-Per-Page" in headers

    assert headers["X-Total-Count"] == str(lenght)
    # assert headers['X-Total-Page'] == str(int(lenght / limit))
    assert headers["X-Page"] == str(int(offset / limit) + 1)
    assert headers["X-Per-Page"] == str(limit)

    if offset == 0:
        assert headers["Link"] == (
            f'<http://testserver/the-beans-should-not-have-sugar?limit={limit}&offset={limit}>; rel="next", '
            f'<http://testserver/the-beans-should-not-have-sugar?limit={limit}&offset={lenght - limit if lenght - limit>= 0 else 0}>; rel="last"'
        )
    elif offset + limit >= lenght:
        previous_offset = offset - limit if offset - limit >= 0 else 0

        if previous_offset:
            previous_offset_section = f"&offset={previous_offset}"

        else:
            previous_offset_section = ""

        assert headers["Link"] == (
            f'<http://testserver/the-beans-should-not-have-sugar?limit={limit}>; rel="first", '
            f'<http://testserver/the-beans-should-not-have-sugar?limit={limit}{previous_offset_section}>; rel="previous"'
        )
    else:
        raise NotImplemented("This case is not implemented")


def assert_no_pagination(headers: dict, limit, offset, lenght):
    assert "Link" not in headers
    assert "X-Total-Count" not in headers
    assert "X-Page" not in headers
    assert "X-Per-Page" not in headers


class GetCohortSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    never_ends = serpy.Field()
    private = serpy.Field()
    language = serpy.Field()
    current_day = serpy.Field()
    current_module = serpy.Field()
    stage = serpy.Field()
    online_meeting_url = serpy.Field()
    timezone = serpy.Field()
    schedule = serpy.MethodField()
    syllabus_version = serpy.MethodField()
    academy = serpy.MethodField()

    def get_schedule(self, obj):
        return obj.schedule.id if obj.schedule else None

    def get_syllabus_version(self, obj):
        return obj.syllabus_version.id if obj.syllabus_version else None

    def get_academy(self, obj):
        return obj.academy.id if obj.academy else None


def serialize_cache_value(data):
    return (
        str(data)
        .replace("'", '"')
        .replace("None", "null")
        .replace("True", "true")
        .replace("False", "false")
        .encode("utf-8")
    )


class CustomTestView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(cache=CohortCache, sort="name", paginate=True)

    def get(self, request, id=None):
        handler = self.extensions(request)

        cache = handler.cache.get()
        if cache is not None:
            return cache

        if id:
            item = Cohort.objects.filter(id=id).first()
            if not item:
                raise ValidationException("Not found", code=404)

            serializer = GetCohortSerializer(item, many=False)
            return handler.response(serializer.data)

        lookups = {}

        if name := request.GET.get("name"):
            lookups["name__in"] = name.split(",")

        if slug := request.GET.get("slug"):
            lookups["slug__in"] = slug.split(",")

        items = Cohort.objects.filter(**lookups)
        items = handler.queryset(items)
        serializer = GetCohortSerializer(items, many=True)

        return handler.response(serializer.data)


class PaginateFalseTestView(CustomTestView):
    extensions = APIViewExtensions(cache=CohortCache, sort="name", paginate=False)


class CachePerUserTestView(CustomTestView):
    extensions = APIViewExtensions(cache=CohortCache, cache_per_user=True, sort="name", paginate=False)


class CachePrefixTestView(CustomTestView):
    extensions = APIViewExtensions(
        cache=CohortCache, cache_prefix="the-beans-should-not-have-sugar", sort="name", paginate=False
    )


class ApiViewExtensionsGetTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    def test_cache__get__spy_the_extensions(self):
        cache.clear()

        # keep before cache handling
        slug = self.bc.fake.slug()
        self.bc.database.delete("admissions.Cohort")
        model = self.bc.database.create(cohort={"slug": slug})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()
        view(request)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

    """
    🔽🔽🔽 Spy the extension arguments
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_cache__get__spy_the_extension_arguments__view1(self):
        cache.clear()

        # keep before cache handling
        slug = self.bc.fake.slug()
        self.bc.database.delete("admissions.Cohort")
        model = self.bc.database.create(cohort={"slug": slug})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()
        view(request)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=CohortCache, sort="name", paginate=True),
            ],
        )

    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_cache__get__spy_the_extension_arguments__view2(self):
        cache.clear()

        # keep before cache handling
        slug = self.bc.fake.slug()
        self.bc.database.delete("admissions.Cohort")
        model = self.bc.database.create(cohort={"slug": slug})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CachePerUserTestView.as_view()
        view(request)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=CohortCache, cache_per_user=True, sort="name", paginate=False),
            ],
        )

    @patch.object(APIViewExtensionHandlers, "_spy_extension_arguments", MagicMock())
    def test_cache__get__spy_the_extension_arguments__view3(self):
        cache.clear()

        # keep before cache handling
        slug = self.bc.fake.slug()
        self.bc.database.delete("admissions.Cohort")
        model = self.bc.database.create(cohort={"slug": slug})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CachePrefixTestView.as_view()
        view(request)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extension_arguments.call_args_list,
            [
                call(cache=CohortCache, cache_prefix="the-beans-should-not-have-sugar", sort="name", paginate=False),
            ],
        )

    """
    🔽🔽🔽 Cache
    """

    def test_cache__get__without_cache__zero_cohorts(self):
        cache.clear()

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")

        key = "Cohort__" + urllib.parse.urlencode(
            sorted(
                {
                    "request.path": "/the-beans-should-not-have-sugar",
                }.items()
            )
        )

        view = CustomTestView.as_view()

        response = view(request)
        expected = []

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(cohort_cache.keys(), {key})

    def test_cache__get__without_cache__one_cohort(self):
        cache.clear()

        model = self.bc.database.create(cohort=1)

        key = "Cohort__" + urllib.parse.urlencode(
            sorted(
                {
                    "request.path": "/the-beans-should-not-have-sugar",
                }.items()
            )
        )

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")

        view = CustomTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer([model.cohort], many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(cohort_cache.keys(), {key})

    def test_cache__get__without_cache__ten_cohorts(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        key = "Cohort__" + urllib.parse.urlencode(
            sorted(
                {
                    "request.path": "/the-beans-should-not-have-sugar",
                }.items()
            )
        )

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")

        view = CustomTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(cohort_cache.keys(), {key})

    def test_cache__get__without_cache__ten_cohorts__passing_arguments(self):
        cache.clear()

        cohorts = [{"name": bin(x).replace("0b", ""), "slug": bin(x).replace("0b", "")} for x in range(0, 8)]
        params = [bin(x).replace("0b", "") for x in range(4, 8)]
        model = self.bc.database.create(cohort=cohorts)

        key = "Cohort__" + urllib.parse.urlencode(
            sorted(
                {
                    "request.path": "/the-beans-should-not-have-sugar",
                    "sort": "slug",
                    "slug": ",".join(params),
                }.items()
            )
        )

        request = APIRequestFactory()
        request = request.get(f'/the-beans-should-not-have-sugar?sort=slug&slug={",".join(params)}')

        view = CustomTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(model.cohort[4:], many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(cohort_cache.keys(), {key})

    def test_cache__get__with_cache(self):
        cache.clear()

        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for expected in cases:
            json_data = json.dumps(expected).encode("utf-8")

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                    }.items()
                )
            )
            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get("/the-beans-should-not-have-sugar")

            view = CustomTestView.as_view()
            response = view(request)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})

    def test_cache__get__with_cache__passing_arguments(self):
        cache.clear()

        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        params = [bin(x).replace("0b", "") for x in range(4, 8)]
        for expected in cases:
            json_data = json.dumps(expected).encode("utf-8")

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": ",".join(params),
                    }.items()
                )
            )
            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get(f'/the-beans-should-not-have-sugar?sort=slug&slug={",".join(params)}')

            view = CustomTestView.as_view()
            response = view(request)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})
            self.assertEqual(cache.get(key), bytes(str(expected).replace("'", '"'), encoding="utf-8"))

    def test_cache__get__with_cache_but_other_case__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            model = self.bc.database.create(cohort={"slug": slug})

            json_data = serialize_cache_object(case)
            cache.set("Cohort__", json_data)
            cache.set("Cohort__keys", {"Cohort__"})

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CustomTestView.as_view()
            response = view(request)
            expected = GetCohortSerializer([model.cohort], many=True).data

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), serialize_cache_object(case))

            res = {
                "headers": {
                    "Content-Type": "application/json",
                },
                "content": serialize_cache_value(expected),
            }
            self.assertEqual(cache.get(key), res)

    def test_cache__get__with_cache_case_of_root_and_current__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            self.bc.database.delete("admissions.Cohort")
            model = self.bc.database.create(cohort={"slug": slug})

            json_data_root = json.dumps(case).encode("utf-8")
            json_data_query = json.dumps(case + case).encode("utf-8")
            cache.set("Cohort__", json_data_root)

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )
            cache.set(key, json_data_query)
            cache.set("Cohort__keys", {"Cohort__", key})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CustomTestView.as_view()
            response = view(request)
            expected = case + case

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), json_data_root)
            self.assertEqual(cache.get(key), json_data_query)

    """
    🔽🔽🔽 Cache per user without auth
    """

    def test_cache_per_user__get__with_cache__passing_arguments(self):
        cache.clear()

        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        params = [bin(x).replace("0b", "") for x in range(4, 8)]
        for expected in cases:
            json_data = json.dumps(expected).encode("utf-8")
            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": None,
                        "sort": "slug",
                        "slug": ",".join(params),
                    }.items()
                )
            )
            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get(f'/the-beans-should-not-have-sugar?sort=slug&slug={",".join(params)}')

            view = CachePerUserTestView.as_view()
            response = view(request)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})
            self.assertEqual(cache.get(key), bytes(str(expected).replace("'", '"'), encoding="utf-8"))

    def test_cache_per_user__get__with_cache_but_other_case__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            model = self.bc.database.create(cohort={"slug": slug})

            json_data = serialize_cache_object(case)
            cache.set("Cohort__", json_data)
            cache.set("Cohort__keys", {"Cohort__"})

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": None,
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CachePerUserTestView.as_view()
            response = view(request)
            expected = GetCohortSerializer([model.cohort], many=True).data

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), serialize_cache_object(case))

            res = {
                "headers": {
                    "Content-Type": "application/json",
                },
                "content": serialize_cache_value(expected),
            }
            self.assertEqual(cache.get(key), res)

    def test_cache_per_user__get__with_cache_case_of_root_and_current__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            self.bc.database.delete("admissions.Cohort")
            model = self.bc.database.create(cohort={"slug": slug})

            json_data_root = json.dumps(case).encode("utf-8")
            json_data_query = json.dumps(case + case).encode("utf-8")
            cache.set("Cohort__", json_data_root)

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": None,
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            cache.set(key, json_data_query)
            cache.set("Cohort__keys", {"Cohort__", key})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CachePerUserTestView.as_view()
            response = view(request)
            expected = case + case

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), json_data_root)
            self.assertEqual(cache.get(key), json_data_query)

    """
    🔽🔽🔽 Cache per user with auth
    """

    def test_cache_per_user__get__auth__with_cache__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        params = [bin(x).replace("0b", "") for x in range(4, 8)]
        for expected in cases:
            cache.clear()

            model = self.bc.database.create(user=1)
            json_data = json.dumps(expected).encode("utf-8")

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": model.user.id,
                        "sort": "slug",
                        "slug": ",".join(params),
                    }.items()
                )
            )
            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get(f'/the-beans-should-not-have-sugar?sort=slug&slug={",".join(params)}')

            force_authenticate(request, user=model.user)
            view = CachePerUserTestView.as_view()
            response = view(request)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})
            self.assertEqual(cache.get(key), bytes(str(expected).replace("'", '"'), encoding="utf-8"))

    def test_cache_per_user__get__auth__with_cache_but_other_case__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            model = self.bc.database.create(cohort={"slug": slug}, user=1)

            json_data = serialize_cache_object(case)
            cache.set("Cohort__", json_data)
            cache.set("Cohort__keys", {"Cohort__"})

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": model.user.id,
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            force_authenticate(request, user=model.user)
            view = CachePerUserTestView.as_view()
            response = view(request)
            expected = GetCohortSerializer([model.cohort], many=True).data

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), serialize_cache_object(case))

            res = {
                "headers": {
                    "Content-Type": "application/json",
                },
                "content": serialize_cache_value(expected),
            }
            self.assertEqual(cache.get(key), res)

    def test_cache_per_user__get__auth__with_cache_case_of_root_and_current__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            self.bc.database.delete("admissions.Cohort")
            model = self.bc.database.create(cohort={"slug": slug}, user=1)

            json_data_root = serialize_cache_object(case)
            json_data_query = serialize_cache_object(case + case)
            cache.set("Cohort__", json_data_root)

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "request.user.id": model.user.id,
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )
            cache.set(key, json_data_query)
            cache.set("Cohort__keys", {"Cohort__", key})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            force_authenticate(request, user=model.user)
            view = CachePerUserTestView.as_view()
            response = view(request)
            expected = case + case

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), json_data_root)
            self.assertEqual(cache.get(key), json_data_query)

    """
    🔽🔽🔽 Cache with prefix
    """

    def test_cache_with_prefix__get__with_cache__passing_arguments(self):
        cache.clear()

        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        params = [bin(x).replace("0b", "") for x in range(4, 8)]
        for expected in cases:
            json_data = json.dumps(expected).encode("utf-8")

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "breathecode.view.get": "the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": ",".join(params),
                    }.items()
                )
            )

            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get(f'/the-beans-should-not-have-sugar?sort=slug&slug={",".join(params)}')

            view = CachePrefixTestView.as_view()
            response = view(request)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})
            self.assertEqual(cache.get(key), bytes(str(expected).replace("'", '"'), encoding="utf-8"))

    def test_cache_with_prefix__get__with_cache_but_other_case__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            model = self.bc.database.create(cohort={"slug": slug})

            json_data = serialize_cache_object(case)
            cache.set("Cohort__", json_data)
            cache.set("Cohort__keys", {"Cohort__"})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CachePrefixTestView.as_view()
            response = view(request)
            expected = GetCohortSerializer([model.cohort], many=True).data

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "breathecode.view.get": "the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                cohort_cache.keys(),
                {
                    "Cohort__",
                    key,
                },
            )
            self.assertEqual(cache.get("Cohort__"), serialize_cache_object(case))

            res = {
                "headers": {
                    "Content-Type": "application/json",
                },
                "content": serialize_cache_value(expected),
            }
            self.assertEqual(cache.get(key), res)

    def test_cache_with_prefix__get__with_cache_case_of_root_and_current__passing_arguments(self):
        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            self.bc.database.delete("admissions.Cohort")
            model = self.bc.database.create(cohort={"slug": slug})

            json_data_root = json.dumps(case).encode("utf-8")
            json_data_query = json.dumps(case + case).encode()
            cache.set("Cohort__", json_data_root)

            key = "Cohort__" + urllib.parse.urlencode(
                sorted(
                    {
                        "request.path": "/the-beans-should-not-have-sugar",
                        "breathecode.view.get": "the-beans-should-not-have-sugar",
                        "sort": "slug",
                        "slug": slug,
                    }.items()
                )
            )

            cache.set(key, json_data_query)
            cache.set("Cohort__keys", {"Cohort__", key})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar?sort=slug&slug={slug}")

            view = CachePrefixTestView.as_view()
            response = view(request)
            expected = case + case

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                cohort_cache.keys(),
                {
                    "Cohort__",
                    key,
                },
            )
            self.assertEqual(cache.get("Cohort__"), json_data_root)
            self.assertEqual(cache.get(key), json_data_query)

    """
    🔽🔽🔽 Sort
    """

    def test_sort__get__ten_cohorts(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")

        view = CustomTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    """
    🔽🔽🔽 Pagination True
    """

    def test_pagination__get__activate__25_cohorts_just_get_20(self):
        cache.clear()

        model = self.bc.database.create(cohort=25)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")

        view = CustomTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name)[:20], many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_pagination(response.headers, limit=20, offset=0, lenght=25)

    def test_pagination__get__activate__with_10_cohorts__get_first_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=0")

        view = CustomTestView.as_view()

        response = view(request)
        expected = {
            "count": 10,
            "first": None,
            "last": "http://testserver/the-beans-should-not-have-sugar?limit=5&offset=5",
            "next": "http://testserver/the-beans-should-not-have-sugar?limit=5&offset=5",
            "previous": None,
            "results": GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name)[:5], many=True).data,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_pagination(response.headers, limit=5, offset=0, lenght=10)

    def test_pagination__get__activate__with_10_cohorts__get_last_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=5")

        view = CustomTestView.as_view()

        response = view(request)
        expected = {
            "count": 10,
            "first": "http://testserver/the-beans-should-not-have-sugar?limit=5",
            "last": None,
            "next": None,
            "previous": "http://testserver/the-beans-should-not-have-sugar?limit=5",
            "results": GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name)[5:], many=True).data,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_pagination(response.headers, limit=5, offset=5, lenght=10)

    def test_pagination__get__activate__with_10_cohorts__after_last_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=10")

        view = CustomTestView.as_view()

        response = view(request)
        expected = {
            "count": 10,
            "first": "http://testserver/the-beans-should-not-have-sugar?limit=5",
            "last": None,
            "next": None,
            "previous": "http://testserver/the-beans-should-not-have-sugar?limit=5&offset=5",
            "results": [],
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_pagination(response.headers, limit=5, offset=10, lenght=10)

    """
    🔽🔽🔽 Pagination False
    """

    def test_pagination__get__deactivate__105_cohorts_just_get_100(self):
        cache.clear()

        model = self.bc.database.create(cohort=105)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar")
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip, deflate, br"

        view = PaginateFalseTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(brotli.decompress(response.content)), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_no_pagination(response.headers, limit=20, offset=0, lenght=25)

    def test_pagination__get__deactivate__with_10_cohorts__get_first_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=0")

        view = PaginateFalseTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_no_pagination(response.headers, limit=20, offset=0, lenght=25)

    def test_pagination__get__deactivate__with_10_cohorts__get_last_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=5")

        view = PaginateFalseTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_no_pagination(response.headers, limit=20, offset=0, lenght=25)

    def test_pagination__get__deactivate__with_10_cohorts__after_last_five(self):
        cache.clear()

        model = self.bc.database.create(cohort=10)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar?limit=5&offset=10")

        view = PaginateFalseTestView.as_view()

        response = view(request)
        expected = GetCohortSerializer(sorted(model.cohort, key=lambda x: x.name), many=True).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert_no_pagination(response.headers, limit=20, offset=0, lenght=25)


class ApiViewExtensionsGetIdTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Spy the extensions
    """

    @patch.object(APIViewExtensionHandlers, "_spy_extensions", MagicMock())
    def test_cache__get__spy_the_extensions(self):
        cache.clear()

        # keep before cache handling
        slug = self.bc.fake.slug()
        self.bc.database.delete("admissions.Cohort")
        model = self.bc.database.create(cohort={"slug": slug})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()
        view(request, id=1)

        self.assertEqual(
            APIViewExtensionHandlers._spy_extensions.call_args_list,
            [
                call(
                    ["CacheExtension", "LanguageExtension", "LookupExtension", "PaginationExtension", "SortExtension"]
                ),
            ],
        )

    """
    🔽🔽🔽 Cache
    """

    def test_cache__get__without_cache__zero_cohorts(self):
        cache.clear()

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"detail": "Not found", "status_code": 404}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(cohort_cache.keys(), set())

    def test_cache__get__without_cache__one_cohort(self):
        cache.clear()

        model = self.bc.database.create(cohort=1)

        request = APIRequestFactory()
        request = request.get("/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()

        response = view(request, id=1)
        expected = GetCohortSerializer(model.cohort, many=False).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        key = "Cohort__id=1&" + urllib.parse.urlencode(
            {
                **request.GET,
                "request.path": "/the-beans-should-not-have-sugar/1",
            }
        )
        self.assertEqual(cohort_cache.keys(), {key})

        res = {
            "headers": {
                "Content-Type": "application/json",
            },
            "content": serialize_cache_value(expected),
        }
        self.assertEqual(cache.get(key), res)

    def test_cache__get__with_cache(self):
        cache.clear()

        cases = [[], [{"x": 1}], [{"x": 1}, {"x": 2}]]
        for expected in cases:
            json_data = json.dumps(expected).encode("utf-8")
            key = "Cohort__id=1&" + urllib.parse.urlencode(
                {
                    "request.path": "/the-beans-should-not-have-sugar/1",
                }
            )
            cache.set(key, json_data)
            cache.set("Cohort__keys", {key})

            request = APIRequestFactory()
            request = request.get("/the-beans-should-not-have-sugar/1")

            view = CustomTestView.as_view()
            response = view(request, id=1)

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {key})
            self.assertEqual(cache.get(key), serialize_cache_value(expected))

    def test_cache__get__with_cache_but_other_case(self):
        cache.clear()
        case = {"x": 1}

        # keep before cache handling
        slug = self.bc.fake.slug()
        model = self.bc.database.create(cohort={"slug": slug})

        json_data = serialize_cache_object(case)
        key1 = "Cohort__id=1&" + urllib.parse.urlencode(
            {
                "request.path": "/the-beans-should-not-have-sugar/1",
            }
        )
        key2 = "Cohort__id=2&" + urllib.parse.urlencode(
            {
                "request.path": "/the-beans-should-not-have-sugar/1",
            }
        )
        cache.set("Cohort__", json_data)
        cache.set(key2, json_data)
        cache.set("Cohort__keys", {"Cohort__", key2})

        request = APIRequestFactory()
        request = request.get(f"/the-beans-should-not-have-sugar/1")

        view = CustomTestView.as_view()
        response = view(request, id=1)
        expected = GetCohortSerializer(model.cohort, many=False).data

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cohort_cache.keys(), {"Cohort__", key1, key2})
        self.assertEqual(cache.get("Cohort__"), serialize_cache_object(case))

        res = {
            "headers": {
                "Content-Type": "application/json",
            },
            "content": serialize_cache_value(expected),
        }
        self.assertEqual(cache.get(key1), res)
        self.assertEqual(cache.get(key2), json_data)

    def test_cache__get__with_cache_case_of_root_and_current(self):
        cases = [({"x": 1}, {"y": 1}), ({"x": 2}, {"y": 2}), ({"x": 3}, {"y": 3})]
        for case in cases:
            cache.clear()

            # keep before cache handling
            slug = self.bc.fake.slug()
            self.bc.database.delete("admissions.Cohort")
            model = self.bc.database.create(cohort={"slug": slug})

            json_data_root = ("application/json    " + json.dumps(case[0])).encode("utf-8")
            json_data_query = ("application/json    " + json.dumps(case[1])).encode("utf-8")
            cache.set("Cohort__", json_data_root)
            key = "Cohort__id=1&" + urllib.parse.urlencode(
                {
                    "request.path": "/the-beans-should-not-have-sugar/1",
                }
            )
            cache.set(key, json_data_query)
            cache.set("Cohort__keys", {"Cohort__", key})

            request = APIRequestFactory()
            request = request.get(f"/the-beans-should-not-have-sugar/1")

            view = CustomTestView.as_view()
            response = view(request, id=1)
            key = "Cohort__id=1&" + urllib.parse.urlencode(
                {
                    **request.GET,
                    "request.path": "/the-beans-should-not-have-sugar/1",
                }
            )
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            expected = case[1]

            self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(cohort_cache.keys(), {"Cohort__", key})
            self.assertEqual(cache.get("Cohort__"), json_data_root)
            self.assertEqual(cache.get(key), json_data_query)
