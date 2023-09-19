from datetime import datetime, timedelta
import random
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.admissions import tasks

from ..mixins import AdmissionsTestCase

UTC_NOW = timezone.now()


def academy_serializer(academy):
    return {
        'id': academy.id,
        'name': academy.name,
        'slug': academy.slug,
    }


def cohort_serializer(cohort):
    return {
        'id': cohort.id,
        'name': cohort.name,
        'slug': cohort.slug,
    }


def user_serializer(user):
    return {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def cohort_set_serializer(cohort_set, cohorts, academy):
    return {
        'academy': academy_serializer(academy),
        'cohorts': [cohort_serializer(cohort) for cohort in cohorts],
        'id': cohort_set.id,
        'slug': cohort_set.slug,
    }


def post_serializer(self, i_owe_you, cohort_set, cohorts=[], academy=None, user=None, data={}):
    return {
        'academy': academy_serializer(academy),
        'id': i_owe_you.id,
        'invoices': [],
        'next_payment_at': self.bc.datetime.to_iso_string(i_owe_you.next_payment_at),
        'plans': [],
        'selected_cohort_set': cohort_set_serializer(cohort_set, cohorts, academy),
        'selected_event_type_set': i_owe_you.selected_event_type_set,
        'selected_mentorship_service_set': i_owe_you.selected_mentorship_service_set,
        'status': i_owe_you.status,
        'status_message': i_owe_you.status_message,
        'user': user_serializer(user),
        'valid_until':
        self.bc.datetime.to_iso_string(i_owe_you.valid_until) if i_owe_you.valid_until else None,
        **data,
    }


def cohort_user_field(data={}):
    return {
        'cohort_id': 0,
        'educational_status': 'ACTIVE',
        'finantial_status': None,
        'id': 0,
        'role': 'STUDENT',
        'user_id': 0,
        'watching': False,
        'history_log': {},
        **data,
    }


class CohortIdUserIdTestSuite(AdmissionsTestCase):
    # When: no auth
    # Then: should return 401
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test__post__no_auth(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 999})

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: no cohort
    # Then: should return 404
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__no_cohort(self):
        """Test /cohort/:id/user without auth"""
        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 999})
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [])

    # When: no have a PlanFinancing or Subscription belonging to the user
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__not_subscribed(self):
        if random.randint(0, 1):
            cohort = {
                'never_ends': True,
                'ending_date': None,
            }

        else:
            cohort = {
                'never_ends': False,
                'ending_date': timezone.now() + timedelta(days=1),
            }

        model = self.bc.database.create(user=1, cohort=cohort)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 1})

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'not-subscribed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])
        self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
        self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [])

    # When: have one of PlanFinancing or Subscription belonging to the user
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__have_a_subscription_or_a_plan_financing(self):
        if random.randint(0, 1):
            cohort = {
                'never_ends': True,
                'ending_date': None,
            }

        else:
            cohort = {
                'never_ends': False,
                'ending_date': timezone.now() + timedelta(days=1),
            }

        if is_a_subscription := random.randint(0, 1):
            extra = {
                'subscription': {
                    'joined_cohorts': [],
                    'valid_until': timezone.now() + timedelta(days=1) if random.randint(0, 1) else None,
                },
            }

        else:
            extra = {
                'plan_financing': {
                    'joined_cohorts': [],
                    'valid_until': timezone.now() + timedelta(days=1),
                    'plan_expires_at': timezone.now() + timedelta(days=1),
                    'monthly_price': random.randint(1, 100),
                },
            }

        model = self.bc.database.create(user=1, cohort=cohort, cohort_set=1, **extra)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 1})

        response = self.client.post(url)
        json = response.json()
        resource = model.subscription if is_a_subscription else model.plan_financing
        expected = post_serializer(self,
                                   resource,
                                   model.cohort_set, [model.cohort],
                                   model.academy,
                                   model.user,
                                   data={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

        if is_a_subscription:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
                self.bc.format.to_dict(model.subscription),
            ])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        else:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
                self.bc.format.to_dict(model.plan_financing),
            ])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [call(1, 1, 'STUDENT')])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [call(1, 1, 'student')])

    # When: joined to cohort externally to subscription
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__joined_to_cohort(self):
        if random.randint(0, 1):
            cohort = {
                'never_ends': True,
                'ending_date': None,
            }

        else:
            cohort = {
                'never_ends': False,
                'ending_date': timezone.now() + timedelta(days=1),
            }

        if is_a_subscription := random.randint(0, 1):
            extra = {
                'subscription': {
                    'joined_cohorts': [],
                    'valid_until': timezone.now() + timedelta(days=1) if random.randint(0, 1) else None,
                },
            }

        else:
            extra = {
                'plan_financing': {
                    'joined_cohorts': [],
                    'valid_until': timezone.now() + timedelta(days=1),
                    'plan_expires_at': timezone.now() + timedelta(days=1),
                    'monthly_price': random.randint(1, 100),
                },
            }
        model = self.bc.database.create(user=1, cohort=cohort, cohort_set=1, cohort_user=1, **extra)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 1})

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'already-joined-to-cohort', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            self.bc.format.to_dict(model.cohort_user),
        ])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

        if is_a_subscription:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
                self.bc.format.to_dict(model.subscription),
            ])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        else:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
                self.bc.format.to_dict(model.plan_financing),
            ])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [])

    # When: rejoining to cohort from a subscription
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__rejoining_from_a_subscription(self):
        if random.randint(0, 1):
            cohort = {
                'never_ends': True,
                'ending_date': None,
            }

        else:
            cohort = {
                'never_ends': False,
                'ending_date': timezone.now() + timedelta(days=1),
            }

        if is_a_subscription := random.randint(0, 1):
            extra = {
                'subscription': {
                    'joined_cohorts': [1],
                    'valid_until': timezone.now() + timedelta(days=1) if random.randint(0, 1) else None,
                },
            }

        else:
            extra = {
                'plan_financing': {
                    'joined_cohorts': [1],
                    'valid_until': timezone.now() + timedelta(days=1),
                    'plan_expires_at': timezone.now() + timedelta(days=1),
                    'monthly_price': random.randint(1, 100),
                },
            }
        model = self.bc.database.create(user=1, cohort=cohort, cohort_set=1, **extra)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 1})

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'already-joined', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

        if is_a_subscription:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
                self.bc.format.to_dict(model.subscription),
            ])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        else:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
                self.bc.format.to_dict(model.plan_financing),
            ])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [])

    # When: joined to another endable cohort
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__joined_to_another_endable_cohort(self):
        cohort = {
            'never_ends': False,
            'ending_date': timezone.now() + timedelta(days=1),
        }

        if is_a_subscription := random.randint(0, 1):
            extra = {
                'subscription': {
                    'joined_cohorts': [2],
                    'valid_until': timezone.now() + timedelta(days=1) if random.randint(0, 1) else None,
                },
            }

        else:
            extra = {
                'plan_financing': {
                    'joined_cohorts': [2],
                    'valid_until': timezone.now() + timedelta(days=1),
                    'plan_expires_at': timezone.now() + timedelta(days=1),
                    'monthly_price': random.randint(1, 100),
                },
            }
        model = self.bc.database.create(user=1, cohort=(2, cohort), cohort_set=1, **extra)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': 1})

        response = self.client.post(url)
        json = response.json()
        expected = {'detail': 'already-joined-to-another-cohort', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

        if is_a_subscription:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
                self.bc.format.to_dict(model.subscription),
            ])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

        else:
            self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
            self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
                self.bc.format.to_dict(model.plan_financing),
            ])

        self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [])
        self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [])

    # When: joined to another endable cohort
    # Then: should return 400
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.tasks.build_cohort_user.delay', MagicMock())
    @patch('breathecode.admissions.tasks.build_profile_academy.delay', MagicMock())
    def test__post__joined_to_another_endable_cohort(self):
        endable = {
            'never_ends': False,
            'ending_date': timezone.now() + timedelta(days=1),
        }
        no_endable = {
            'never_ends': True,
            'ending_date': None,
        }

        cohorts = [
            (endable, no_endable),
            (no_endable, endable),
            (no_endable, no_endable),
        ]

        id = 0
        for cohort1, cohort2 in cohorts:
            if is_a_subscription := random.randint(0, 1):
                extra = {
                    'subscription': {
                        'joined_cohorts': [id + 2],
                        'valid_until': timezone.now() + timedelta(days=1) if random.randint(0, 1) else None,
                    },
                }

            else:
                extra = {
                    'plan_financing': {
                        'joined_cohorts': [id + 2],
                        'valid_until': timezone.now() + timedelta(days=1),
                        'plan_expires_at': timezone.now() + timedelta(days=1),
                        'monthly_price': random.randint(1, 100),
                    },
                }

            model = self.bc.database.create(user=1, cohort=[cohort1, cohort2], cohort_set=1, **extra)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('admissions:cohort_id_join', kwargs={'cohort_id': id + 1})

            response = self.client.post(url)
            json = response.json()
            resource = model.subscription if is_a_subscription else model.plan_financing
            expected = post_serializer(self,
                                       resource,
                                       model.cohort_set, [model.cohort[0], model.cohort[1]],
                                       model.academy,
                                       model.user,
                                       data={})

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
            self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

            if is_a_subscription:
                self.assertEqual(self.bc.database.list_of('payments.Subscription'), [
                    self.bc.format.to_dict(model.subscription),
                ])
                self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [])

            else:
                self.assertEqual(self.bc.database.list_of('payments.Subscription'), [])
                self.assertEqual(self.bc.database.list_of('payments.PlanFinancing'), [
                    self.bc.format.to_dict(model.plan_financing),
                ])

            self.bc.check.calls(tasks.build_cohort_user.delay.call_args_list, [
                call(model.cohort[0].id, model.user.id, 'STUDENT'),
            ])
            self.bc.check.calls(tasks.build_profile_academy.delay.call_args_list, [
                call(model.academy.id, model.user.id, 'student'),
            ])

            id += 2

            # teardown
            self.bc.database.delete('admissions.CohortUser')
            self.bc.database.delete('authenticate.ProfileAcademy')
            self.bc.database.delete('payments.Subscription')
            self.bc.database.delete('payments.PlanFinancing')

            tasks.build_cohort_user.delay.call_args_list = []
            tasks.build_profile_academy.delay.call_args_list = []
