"""
Test /academy/lead
"""
import random
from random import choice, choices, randint
from unittest.mock import patch, MagicMock
from django.urls.base import reverse_lazy
from rest_framework import status
from faker import Faker
from ..mixins import MarketingTestCase

fake = Faker()


def course_translation_serializer(course_translation):
    return {
        'description': course_translation.description,
        'lang': course_translation.lang,
        'title': course_translation.title,
    }


def get_serializer(course, academy, syllabus, course_translation=None, data={}):
    if course_translation:
        course_translation = course_translation_serializer(course_translation)

    return {
        'slug': course.slug,
        'icon_url': course.icon_url,
        'academy': academy.id,
        'syllabus': syllabus.id,
        'course_translation': course_translation,
        **data,
    }


class LeadTestSuite(MarketingTestCase):
    """
    🔽🔽🔽 Zero Course
    """

    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_zero_courses(self):
        url = reverse_lazy('marketing:course')

        response = self.client.get(url, format='json')
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('marketing.Course'), [])
        self.assertEqual(self.bc.database.list_of('marketing.CourseTranslation'), [])

    """
    🔽🔽🔽 Two Course
    """

    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_two_courses__status_active__visibility_public(self):
        courses = [{'status': 'ACTIVE', 'visibility': 'PUBLIC'} for _ in range(2)]
        model = self.bc.database.create(course=courses)

        url = reverse_lazy('marketing:course')

        response = self.client.get(url, format='json')
        json = response.json()

        expected = [
            get_serializer(model.course[1], model.academy, model.syllabus),
            get_serializer(model.course[0], model.academy, model.syllabus),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('marketing.Course'), self.bc.format.to_dict(model.course))
        self.assertEqual(self.bc.database.list_of('marketing.CourseTranslation'), [])

    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_two_courses__wrong_status__wrong_visibility(self):
        courses = [{
            'status': random.choice(['ARCHIVED', 'DELETED']),
            'visibility': random.choice(['UNLISTED', 'PRIVATE'])
        } for _ in range(2)]
        model = self.bc.database.create(course=courses)

        url = reverse_lazy('marketing:course')

        response = self.client.get(url, format='json')
        json = response.json()

        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('marketing.Course'), self.bc.format.to_dict(model.course))
        self.assertEqual(self.bc.database.list_of('marketing.CourseTranslation'), [])

    """
    🔽🔽🔽 Two Course with one CourseTranslation each one
    """

    @patch('breathecode.notify.utils.hook_manager.HookManagerClass.process_model_event', MagicMock())
    def test_two_courses__status_active__visibility_public__with_course_translation(self):
        courses = [{'status': 'ACTIVE', 'visibility': 'PUBLIC'} for _ in range(2)]
        course_translations = [{
            'lang':
            'en' + (f'-{random.choice(["US", "UK"])}' if random.choice([True, False]) else ''),
            'course_id':
            n
        } for n in range(1, 3)]

        model = self.bc.database.create(course=courses, course_translation=course_translations)

        url = reverse_lazy('marketing:course')

        response = self.client.get(url, format='json')
        json = response.json()

        expected = [
            get_serializer(model.course[1], model.academy, model.syllabus, model.course_translation[1]),
            get_serializer(model.course[0], model.academy, model.syllabus, model.course_translation[0]),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of('marketing.Course'), self.bc.format.to_dict(model.course))
        self.assertEqual(self.bc.database.list_of('marketing.CourseTranslation'),
                         self.bc.format.to_dict(model.course_translation))
