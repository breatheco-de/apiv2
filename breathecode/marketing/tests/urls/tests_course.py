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
        "lang": course_translation.lang,
        "title": course_translation.title,
        "landing_url": course_translation.landing_url,
        "video_url": course_translation.video_url,
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
        "course_translation": course_translation,
        "cohorts_group": [],
        "cohorts_order": None,
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
