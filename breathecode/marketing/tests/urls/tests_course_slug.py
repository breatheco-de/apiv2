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


def get_serializer(course, academy, syllabus=[], course_translation=None, data={}):

    if course_translation:
        course_translation = course_translation_serializer(course_translation)

    return {
        "slug": course.slug,
        "icon_url": course.icon_url,
        "technologies": course.technologies,
        "academy": academy_serializer(academy),
        "syllabus": [syllabus_serializer(x) for x in syllabus],
        "course_translation": course_translation,
        "status": course.status,
        "visibility": course.visibility,
        "cohort": course.cohort,
        "color": course.color,
        "plan_slug": course.plan_slug,
        **data,
    }


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Zero Course
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_zero_courses(self):
        url = reverse_lazy("marketing:course_slug", kwargs={"course_slug": "gangster"})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = {"detail": "course-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 One Course
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__status_active__good_visibility(self):
        course = {"status": "ACTIVE", "visibility": random.choice(["PUBLIC", "UNLISTED"])}
        model = self.bc.database.create(course=course)

        url = reverse_lazy("marketing:course_slug", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = get_serializer(model.course, model.academy, [model.syllabus])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__wrong_status__wrong_visibility(self):
        course = {
            "status": random.choice(["ARCHIVED", "DELETED"]),
            "visibility": "PRIVATE",
        }
        model = self.bc.database.create(course=course)

        url = reverse_lazy("marketing:course_slug", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = {"detail": "course-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(self.bc.database.list_of("marketing.CourseTranslation"), [])

    """
    🔽🔽🔽 One Course with one CourseTranslation in english
    """

    @patch("breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event", MagicMock())
    def test_one_course__status_active__good_visibility__with_course_translation(self):
        course = {"status": "ACTIVE", "visibility": random.choice(["PUBLIC", "UNLISTED"])}
        course_translation = {"lang": "en"}
        if random.choice([True, False]):
            course_translation["lang"] += f'-{random.choice(["US", "UK"])}'

        model = self.bc.database.create(course=course, course_translation=course_translation)

        url = reverse_lazy("marketing:course_slug", kwargs={"course_slug": model.course.slug})

        response = self.client.get(url, format="json")
        json = response.json()

        expected = get_serializer(model.course, model.academy, [model.syllabus], model.course_translation)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("marketing.Course"), [self.bc.format.to_dict(model.course)])
        self.assertEqual(
            self.bc.database.list_of("marketing.CourseTranslation"),
            [
                self.bc.format.to_dict(model.course_translation),
            ],
        )
