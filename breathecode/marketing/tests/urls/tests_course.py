"""
Test /academy/lead
"""

import random
from random import choice, choices, randint
from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from faker import Faker
from rest_framework import status

from ..mixins import MarketingTestCase

fake = Faker()


def course_translation_serializer(course_translation):
    return {
        "course_modules": course_translation.course_modules,
        "landing_variables": course_translation.landing_variables,
        "description": course_translation.description,
        "short_description": course_translation.short_description,
        "featured_assets": course_translation.featured_assets,
        "lang": course_translation.lang,
        "title": course_translation.title,
        "landing_url": course_translation.landing_url,
        "preview_url": course_translation.preview_url,
        "video_url": course_translation.video_url,
        "heading": course_translation.heading,
        "prerequisite": course_translation.prerequisite,
    }


def academy_serializer(academy):
    return {
        "icon_url": academy.icon_url,
        "id": academy.id,
        "logo_url": academy.logo_url,
        "name": academy.name,
        "slug": academy.slug,
    }


def syllabus_serializer(syllabus):
    return {
        "id": syllabus.id,
        "logo": syllabus.logo,
        "name": syllabus.name,
        "slug": syllabus.slug,
    }


def get_serializer(course, academy, syllabus=[], course_translation=None, cohort=None, data={}):
    if course_translation:
        course_translation = course_translation_serializer(course_translation)

    return {
        "slug": course.slug,
        "icon_url": course.icon_url,
        "color": course.color,
        "status": course.status,
        "visibility": course.visibility,
        "technologies": course.technologies,
        "academy": academy_serializer(academy),
        "cohort": cohort.id if cohort else None,
        "syllabus": [syllabus_serializer(x) for x in syllabus],
        "plan_slug": course.plan_slug,
        "is_listed": course.is_listed,
        "course_translation": course_translation,
        "banner_image": course.banner_image,
        **data,
    }


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Zero Course
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_zero_courses(self):
        url = reverse_lazy("marketing:course")

        response = self.client.get(url, format="json")
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 Two Course
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_two_courses__status_active__visibility_public(self):
        courses = [{"status": "ACTIVE", "visibility": "PUBLIC"} for _ in range(2)]
        model = self.bc.database.create(course=courses)

        url = reverse_lazy("marketing:course")

        response = self.client.get(url, format="json")
        json = response.json()

        expected = [
            get_serializer(model.course[1], model.academy, [model.syllabus]),
            get_serializer(model.course[0], model.academy, [model.syllabus]),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), self.bc.format.to_dict(model.course))
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_two_courses__wrong_status__wrong_visibility(self):
        courses = [
            {"status": random.choice(["ARCHIVED", "DELETED"]), "visibility": random.choice(["UNLISTED", "PRIVATE"])}
            for _ in range(2)
        ]
        model = self.bc.database.create(course=courses)

        url = reverse_lazy("marketing:course")

        response = self.client.get(url, format="json")
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), self.bc.format.to_dict(model.course))
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 Two Course with one CourseTranslation each one
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_two_courses__status_active__visibility_public__with_course_translation(self):
        courses = [{"status": "ACTIVE", "visibility": "PUBLIC"} for _ in range(2)]
        course_translations = [
            {"lang": "en" + (f'-{random.choice(["US", "UK"])}' if random.choice([True, False]) else ""), "course_id": n}
            for n in range(1, 3)
        ]

        model = self.bc.database.create(course=courses, course_translation=course_translations)

        url = reverse_lazy("marketing:course")

        response = self.client.get(url, format="json")
        json = response.json()

        expected = [
            get_serializer(model.course[1], model.academy, [model.syllabus], model.course_translation[1]),
            get_serializer(model.course[0], model.academy, [model.syllabus], model.course_translation[0]),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), self.bc.format.to_dict(model.course))
        self.assertEqual(
            self.bc.database.list_of("marketing.CourseTranslation"), self.bc.format.to_dict(model.course_translation)
        )


class CourseTranslationsTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Zero Course
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_zero_courses(self):
        url = reverse_lazy("marketing:course_translations", kwargs={"course_slug": "gangster"})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = {"detail": "course-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 One Course with no translations
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__status_active__good_visibility__no_translations(self):
        course = {"status": "ACTIVE", "visibility": random.choice(["PUBLIC", "UNLISTED"])}
        model = self.bc.database.create(course=course)

        url = reverse_lazy("marketing:course_translations", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 One Course with multiple translations
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__status_active__good_visibility__with_translations(self):
        course = {"status": "ACTIVE", "visibility": random.choice(["PUBLIC", "UNLISTED"])}
        course_translations = [
            {"lang": "en"},
            {"lang": "es"},
            {"lang": "pt"},
        ]
        model = self.bc.database.create(course=course, course_translation=course_translations)

        url = reverse_lazy("marketing:course_translations", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = [
            course_translation_serializer(model.course_translation[0]),
            course_translation_serializer(model.course_translation[1]),
            course_translation_serializer(model.course_translation[2]),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(
            self.bc.database.list_of("marketing.CourseTranslation"),
            self.bc.format.to_dict(model.course_translation),
        )

    """
    🔽🔽🔽 One Course with wrong status
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__wrong_status__with_translations(self):
        course = {
            "status": random.choice(["ARCHIVED", "DELETED"]),
            "visibility": random.choice(["PUBLIC", "UNLISTED"]),
        }
        course_translations = [
            {"lang": "en"},
            {"lang": "es"},
        ]
        model = self.bc.database.create(course=course, course_translation=course_translations)

        url = reverse_lazy("marketing:course_translations", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = {"detail": "course-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(
            self.bc.database.list_of("marketing.CourseTranslation"),
            self.bc.format.to_dict(model.course_translation),
        )

    """
    🔽🔽🔽 One Course with wrong visibility
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__wrong_visibility__with_translations(self):
        course = {
            "status": "ACTIVE",
            "visibility": "PRIVATE",
        }
        course_translations = [
            {"lang": "en"},
            {"lang": "es"},
        ]
        model = self.bc.database.create(course=course, course_translation=course_translations)

        url = reverse_lazy("marketing:course_translations", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = {"detail": "course-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(
            self.bc.database.list_of("marketing.CourseTranslation"),
            self.bc.format.to_dict(model.course_translation),
        )
