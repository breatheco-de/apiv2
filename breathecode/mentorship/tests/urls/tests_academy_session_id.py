"""
This file just can contains duck tests refert to AcademyInviteView
"""
from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from django.utils import timezone
from breathecode.mentorship import signals

from ..mixins import MentorshipTestCase
from django.utils import timezone

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_serializer(self, mentorship_session, mentor_profile, mentorship_service, user, data={}):
    return {
        'accounted_duration': mentorship_session.accounted_duration,
        'agenda': mentorship_session.agenda,
        'bill': mentorship_session.bill,
        'allow_billing': mentorship_session.allow_billing,
        'starts_at': format_datetime(self, mentorship_session.starts_at),
        'ends_at': format_datetime(self, mentorship_session.ends_at),
        'started_at': format_datetime(self, mentorship_session.started_at),
        'ended_at': format_datetime(self, mentorship_session.ended_at),
        'id': mentorship_session.id,
        'mentee': user.id,
        'service': mentorship_service.id,
        'mentee_left_at': mentorship_session.mentee_left_at,
        'mentor': mentor_profile.id,
        'is_online': mentorship_session.is_online,
        'latitude': mentorship_session.latitude,
        'longitude': mentorship_session.longitude,
        'mentor_joined_at': mentorship_session.mentor_joined_at,
        'mentor_left_at': mentorship_session.mentor_left_at,
        'status': mentorship_session.status,
        'summary': mentorship_session.summary,
        'name': mentorship_session.name,
        'online_meeting_url': mentorship_session.online_meeting_url,
        'online_recording_url': mentorship_session.online_recording_url,
        **data,
    }


def put_serializer(data={}):
    return {
        'accounted_duration': None,
        'agenda': None,
        'allow_billing': True,
        'bill': None,
        'ended_at': None,
        'ends_at': None,
        'id': 0,
        'is_online': False,
        'latitude': None,
        'longitude': None,
        'mentee': 0,
        'mentee_left_at': None,
        'mentor': 0,
        'mentor_joined_at': None,
        'mentor_left_at': None,
        'name': None,
        'online_meeting_url': None,
        'online_recording_url': None,
        'service': 0,
        'started_at': None,
        'starts_at': None,
        'status': 'PENDING',
        'summary': None,
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__get__without_academy_header(self):
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test__get__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_mentorship_session for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 GET with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self,
                                  model.mentorship_session,
                                  model.mentor_profile,
                                  model.mentorship_service,
                                  model.user,
                                  data={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])

    """
    🔽🔽🔽 PUT capability
    """

    def test__put__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: crud_mentorship_session for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 PUT not found the MentorshipSession
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__not_found(self):
        cases = [
            (1, {}, False),
            (2, {
                'mentorship_session': 1
            }, True),
        ]
        for id, kwargs, has_instance_db in cases:
            model = self.bc.database.create(user=1,
                                            role=1,
                                            capability='crud_mentorship_session',
                                            profile_academy=1,
                                            **kwargs)

            self.bc.request.set_headers(academy=id)
            self.bc.request.authenticate(model.user)

            url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': id})
            response = self.client.put(url)

            json = response.json()
            expected = {'detail': 'not-found', 'status_code': 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
                self.bc.format.to_dict(model.mentorship_session),
            ] if has_instance_db else [])
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])

            # teardown
            self.bc.database.delete('mentorship.MentorshipSession')

    """
    🔽🔽🔽 PUT found a MentorshipSession, with one MentorProfile and MentorshipService
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__without_required_fields(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=1,
                                        mentorship_service=1,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.put(url)

        json = response.json()
        expected = {'mentor': ['This field is required.']}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_required_fields(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=1,
                                        mentorship_service=1,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        data = {'mentor': 1}
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = put_serializer({
            'id': 1,
            'mentee': 1,
            'service': 1,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [])

    """
    🔽🔽🔽 PUT with all required fields, is_online is False
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_all_required_fields__is_online_as_false(self):
        mentorship_bill = {'status': random.choice(['RECALCULATE', 'DUE'])}
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_session = {'status': current_status}

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentorship_service=1,
                                        mentorship_bill=mentorship_bill,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()
        data = {
            'name': self.bc.fake.name(),
            'is_online': False,
            'latitude': random.random() * 180 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'service': 1,
            'mentee': 1,
            'online_meeting_url': self.bc.fake.url(),
            'online_recording_url': self.bc.fake.url(),
            'status': random.choice(statuses),
            'allow_billing': bool(random.randint(0, 1)),
            'bill': 1,
            'agenda': self.bc.fake.text(),
            'summary': self.bc.fake.text(),
            'starts_at': self.bc.datetime.to_iso_string(date),
            'ends_at': self.bc.datetime.to_iso_string(date),
            'started_at': self.bc.datetime.to_iso_string(date),
            'ended_at': self.bc.datetime.to_iso_string(date),
            'mentor_joined_at': self.bc.datetime.to_iso_string(date),
            'mentor_left_at': self.bc.datetime.to_iso_string(date),
            'mentee_left_at': self.bc.datetime.to_iso_string(date),
            'mentor': 1,
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = put_serializer({
            'id': 1,
            'mentee': 1,
            'service': 1,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_fields = ['bill', 'mentee', 'mentor', 'service']
        for key in update_fields:
            data[f'{key}_id'] = data.pop(key)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            {
                **self.bc.format.to_dict(model.mentorship_session),
                **data,
                'starts_at': date,
                'ends_at': date,
                'started_at': date,
                'ended_at': date,
                'mentor_joined_at': date,
                'mentor_left_at': date,
                'mentee_left_at': date,
                'suggested_accounted_duration': timedelta(0),
                'accounted_duration': timedelta(0),
                'status_message': '',
            },
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])
        self.assertEqual(
            signals.mentorship_session_status.send.call_args_list,
            ([
                # mixer
                call(instance=model.mentorship_session, sender=model.mentorship_session.__class__),
            ] if current_status != 'PENDING' else []) + [
                # endpoint
                call(instance=model.mentorship_session, sender=model.mentorship_session.__class__),
            ])

    """
    🔽🔽🔽 PUT with all required fields, is_online is False, MentorshipBill finished
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_all_required_fields__is_online_as_false__bill_finished(self):
        mentorship_bill = {'status': random.choice(['APPROVED', 'PAID', 'IGNORED'])}
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_session = {'status': current_status}

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentorship_service=1,
                                        mentorship_bill=mentorship_bill,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()
        data = {
            'name': self.bc.fake.name(),
            'is_online': False,
            'latitude': random.random() * 180 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'service': 1,
            'mentee': 1,
            'online_meeting_url': self.bc.fake.url(),
            'online_recording_url': self.bc.fake.url(),
            'status': random.choice(statuses),
            'allow_billing': bool(random.randint(0, 1)),
            'bill': 1,
            'agenda': self.bc.fake.text(),
            'summary': self.bc.fake.text(),
            'starts_at': self.bc.datetime.to_iso_string(date),
            'ends_at': self.bc.datetime.to_iso_string(date),
            'started_at': self.bc.datetime.to_iso_string(date),
            'ended_at': self.bc.datetime.to_iso_string(date),
            'mentor_joined_at': self.bc.datetime.to_iso_string(date),
            'mentor_left_at': self.bc.datetime.to_iso_string(date),
            'mentee_left_at': self.bc.datetime.to_iso_string(date),
            'mentor': 1,
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'trying-to-change-a-closed-bill', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            {
                **self.bc.format.to_dict(model.mentorship_session),
            },
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])
        self.assertEqual(
            str(signals.mentorship_session_status.send.call_args_list),
            str([
                call(instance=model.mentorship_session, sender=model.mentorship_session.__class__),
            ] if current_status != 'PENDING' else []))

    """
    🔽🔽🔽 PUT with all required fields, is_online is True, trying to edit readonly fields
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_all_required_fields__is_online_as_true__trying_to_edit_readonly_fields(self):
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=1,
                                        mentorship_service=1,
                                        mentorship_bill=1,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()
        cases = [
            {
                'mentor_joined_at': self.bc.datetime.to_iso_string(date),
            },
            {
                'mentor_left_at': self.bc.datetime.to_iso_string(date),
            },
            {
                'mentee_left_at': self.bc.datetime.to_iso_string(date),
            },
            {
                'started_at': self.bc.datetime.to_iso_string(date),
            },
            {
                'ended_at': self.bc.datetime.to_iso_string(date),
            },
        ]
        for kwargs in cases:
            data = {
                'name': self.bc.fake.name(),
                'is_online': True,
                'latitude': random.random() * 180 * random.choice([1, -1]),
                'longitude': random.random() * 90 * random.choice([1, -1]),
                'longitude': random.random() * 90 * random.choice([1, -1]),
                'service': 1,
                'mentee': 1,
                'online_meeting_url': self.bc.fake.url(),
                'online_recording_url': self.bc.fake.url(),
                'status': random.choice(statuses),
                'allow_billing': bool(random.randint(0, 1)),
                'bill': 1,
                'agenda': self.bc.fake.text(),
                'summary': self.bc.fake.text(),
                'starts_at': self.bc.datetime.to_iso_string(date),
                'ends_at': self.bc.datetime.to_iso_string(date),
                'mentor': 1,
                **kwargs,
            }
            response = self.client.put(url, data, format='json')

            json = response.json()
            expected = {'detail': 'read-only-field-online', 'status_code': 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
                {
                    **self.bc.format.to_dict(model.mentorship_session),
                },
            ])
            self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
                self.bc.format.to_dict(model.mentorship_bill),
            ])
            self.assertEqual(str(signals.mentorship_session_status.send.call_args_list), str([]))

    """
    🔽🔽🔽 PUT with all required fields, is_online is True
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_all_required_fields__is_online_as_true(self):
        mentorship_bill = {'status': random.choice(['RECALCULATE', 'DUE'])}
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_session = {'status': current_status}

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=mentorship_session,
                                        mentorship_service=1,
                                        mentorship_bill=mentorship_bill,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()

        data = {
            'name': self.bc.fake.name(),
            'is_online': True,
            'latitude': random.random() * 180 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'service': 1,
            'mentee': 1,
            'online_meeting_url': self.bc.fake.url(),
            'online_recording_url': self.bc.fake.url(),
            'status': random.choice(statuses),
            'allow_billing': bool(random.randint(0, 1)),
            'bill': 1,
            'agenda': self.bc.fake.text(),
            'summary': self.bc.fake.text(),
            'starts_at': self.bc.datetime.to_iso_string(date),
            'ends_at': self.bc.datetime.to_iso_string(date),
            'mentor': 1,
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = put_serializer({
            'id': 1,
            'mentee': 1,
            'service': 1,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_fields = ['bill', 'mentee', 'mentor', 'service']
        for key in update_fields:
            data[f'{key}_id'] = data.pop(key)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            {
                **self.bc.format.to_dict(model.mentorship_session),
                **data,
                'starts_at': date,
                'ends_at': date,
                'suggested_accounted_duration': timedelta(0),
                'accounted_duration': timedelta(0),
                'status_message': 'No one joined this session, nothing will be accounted for.',
            },
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])

        self.assertEqual(
            signals.mentorship_session_status.send.call_args_list,
            ([
                # mixer
                call(instance=model.mentorship_session, sender=model.mentorship_session.__class__),
            ] if current_status != 'PENDING' else []) + [
                # endpoint
                call(instance=model.mentorship_session, sender=model.mentorship_session.__class__),
            ])

    """
    🔽🔽🔽 PUT with all required fields, is_online is True, MentorshipBill finished
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__with_all_required_fields__is_online_as_true__bill_finished(self):
        mentorship_bill = {'status': random.choice(['APPROVED', 'PAID', 'IGNORED'])}
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=1,
                                        mentorship_service=1,
                                        mentorship_bill=mentorship_bill,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()

        data = {
            'name': self.bc.fake.name(),
            'is_online': True,
            'latitude': random.random() * 180 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'service': 1,
            'mentee': 1,
            'online_meeting_url': self.bc.fake.url(),
            'online_recording_url': self.bc.fake.url(),
            'status': random.choice(statuses),
            'allow_billing': bool(random.randint(0, 1)),
            'bill': 1,
            'agenda': self.bc.fake.text(),
            'summary': self.bc.fake.text(),
            'starts_at': self.bc.datetime.to_iso_string(date),
            'ends_at': self.bc.datetime.to_iso_string(date),
            'mentor': 1,
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = {'detail': 'trying-to-change-a-closed-bill', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        update_fields = ['bill', 'mentee', 'mentor', 'service']
        for key in update_fields:
            data[f'{key}_id'] = data.pop(key)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            {
                **self.bc.format.to_dict(model.mentorship_session),
            },
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            self.bc.format.to_dict(model.mentorship_bill),
        ])
        self.assertEqual(str(signals.mentorship_session_status.send.call_args_list), str([]))

    """
    🔽🔽🔽 PUT passing a MentorshipBill with some MentorshipSession without MentorshipService
    """

    @patch('breathecode.mentorship.signals.mentorship_session_status.send', MagicMock())
    def test__put__found__passing_a_bill_with_some_session_without_service(self):
        mentorship_bill = {'status': 'DUE'}
        statuses = ['PENDING', 'STARTED', 'COMPLETED', 'FAILED', 'IGNORED']
        current_status = random.choice(statuses)
        statuses.remove(current_status)
        mentorship_sessions = [{
            'status': current_status,
            'bill_id': 1,
            'service_id': 1,
        }, {
            'status': current_status,
            'bill_id': 1,
            'service_id': None,
        }]

        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='crud_mentorship_session',
                                        mentorship_session=mentorship_sessions,
                                        mentorship_service=1,
                                        mentorship_bill=mentorship_bill,
                                        mentor_profile=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        date = timezone.now()
        data = {
            'name': self.bc.fake.name(),
            'is_online': False,
            'latitude': random.random() * 180 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'longitude': random.random() * 90 * random.choice([1, -1]),
            'service': 1,
            'mentee': 1,
            'online_meeting_url': self.bc.fake.url(),
            'online_recording_url': self.bc.fake.url(),
            'status': random.choice(statuses),
            'allow_billing': bool(random.randint(0, 1)),
            'bill': 1,
            'agenda': self.bc.fake.text(),
            'summary': self.bc.fake.text(),
            'starts_at': self.bc.datetime.to_iso_string(date),
            'ends_at': self.bc.datetime.to_iso_string(date),
            'started_at': self.bc.datetime.to_iso_string(date),
            'ended_at': self.bc.datetime.to_iso_string(date),
            'mentor_joined_at': self.bc.datetime.to_iso_string(date),
            'mentor_left_at': self.bc.datetime.to_iso_string(date),
            'mentee_left_at': self.bc.datetime.to_iso_string(date),
            'mentor': 1,
        }
        response = self.client.put(url, data, format='json')

        json = response.json()
        expected = put_serializer({
            'id': 1,
            'mentee': 1,
            'service': 1,
            **data,
        })

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        update_fields = ['bill', 'mentee', 'mentor', 'service']
        for key in update_fields:
            data[f'{key}_id'] = data.pop(key)

        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            {
                **self.bc.format.to_dict(model.mentorship_session[0]),
                **data,
                'starts_at': date,
                'ends_at': date,
                'started_at': date,
                'ended_at': date,
                'mentor_joined_at': date,
                'mentor_left_at': date,
                'mentee_left_at': date,
            },
            self.bc.format.to_dict(model.mentorship_session[1]),
        ])
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipBill'), [
            {
                **self.bc.format.to_dict(model.mentorship_bill),
                'status': 'RECALCULATE',
            },
        ])
        self.assertEqual(
            signals.mentorship_session_status.send.call_args_list,
            ([
                # mixer
                call(instance=model.mentorship_session[0], sender=model.mentorship_session[0].__class__),
                call(instance=model.mentorship_session[1], sender=model.mentorship_session[1].__class__),
            ] if current_status != 'PENDING' else []) + [
                # endpoint
                call(instance=model.mentorship_session[0], sender=model.mentorship_session[0].__class__),
            ])
