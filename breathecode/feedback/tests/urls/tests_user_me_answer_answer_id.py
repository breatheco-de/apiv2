"""
Test /answer/:id
"""
import re
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

import breathecode.activity.tasks as activity_tasks
from breathecode.services.datetime_to_iso_format import datetime_to_iso_format
from breathecode.tests.mixins.breathecode_mixin import Breathecode

from ...signals import survey_answered


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    monkeypatch.setattr('breathecode.feedback.signals.survey_answered.send_robust', MagicMock())
    monkeypatch.setattr(activity_tasks.add_activity, 'delay', MagicMock())
    yield


def test_answer_id_without_auth(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': 9999})
    response = client.get(url)
    json = response.json()
    expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert bc.database.list_of('feedback.Answer') == []


def test_answer_id_without_data(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': 9999})
    response = client.get(url)
    json = response.json()
    expected = {
        'detail': 'answer-of-other-user-or-not-exists',
        'status_code': 404,
    }

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of('feedback.Answer') == []


def test_answer_id__answer_of_other_user(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)
    model = bc.database.create(answer=True)
    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    response = client.get(url)
    json = response.json()
    expected = {'detail': 'answer-of-other-user-or-not-exists', 'status_code': 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of('feedback.Answer') == [db]


def test_answer_id_with_data(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT'}
    model = bc.database.create(user=1, answer=True, answer_kwargs=answer_kwargs)
    client.force_authenticate(model.user)

    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    response = client.get(url)
    json = response.json()
    expected = {
        'id': model['answer'].id,
        'title': model['answer'].title,
        'lowest': model['answer'].lowest,
        'highest': model['answer'].highest,
        'lang': model['answer'].lang,
        'score': model['answer'].score,
        'comment': model['answer'].comment,
        'status': model['answer'].status,
        'opened_at': model['answer'].opened_at,
        'created_at': datetime_to_iso_format(model['answer'].created_at),
        'updated_at': datetime_to_iso_format(model['answer'].updated_at),
        'cohort': model['answer'].cohort,
        'academy': model['answer'].academy,
        'mentor': {
            'first_name': model['answer'].mentor.first_name,
            'id': model['answer'].mentor.id,
            'last_name': model['answer'].mentor.last_name,
            'profile': None,
        },
        'user': {
            'first_name': model['answer'].user.first_name,
            'id': model['answer'].user.id,
            'last_name': model['answer'].user.last_name,
            'profile': None,
        },
        'event': model['answer'].event,
    }

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of('feedback.Answer') == [db]


def test_answer_id_put_with_bad_id(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    model = bc.database.create(user=1)
    client.force_authenticate(model.user)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': 9999})
    response = client.put(url, {})
    json = response.json()
    expected = {
        'detail': 'answer-of-other-user-or-not-exists',
        'status_code': 404,
    }

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert survey_answered.send_robust.call_args_list == []
    assert activity_tasks.add_activity.delay.call_args_list == []


def test_answer_id_put_without_score(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT'}
    model = bc.database.create(user=1, answer=True, answer_kwargs=answer_kwargs)
    client.force_authenticate(model.user)
    db = bc.format.to_dict(model.answer)
    data = {
        'comment': 'They killed kenny',
    }
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    response = client.put(url, data)
    json = response.json()

    assert json == {'non_field_errors': ['Score must be between 1 and 10']}
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of('feedback.Answer') == [db]
    assert survey_answered.send_robust.call_args_list == []
    assert activity_tasks.add_activity.delay.call_args_list == []


def test_answer_id_put_with_score_less_of_1(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT'}
    model = bc.database.create(user=1, answer=True, answer_kwargs=answer_kwargs)
    client.force_authenticate(model.user)
    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    data = {
        'comment': 'They killed kenny',
        'score': 0,
    }
    response = client.put(url, data)
    json = response.json()

    assert json == {'non_field_errors': ['Score must be between 1 and 10']}
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of('feedback.Answer') == [db]
    assert survey_answered.send_robust.call_args_list == []
    assert activity_tasks.add_activity.delay.call_args_list == []


def test_answer_id_put_with_score_more_of_10(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT'}
    model = bc.database.create(user=1, answer=True, answer_kwargs=answer_kwargs)
    client.force_authenticate(model.user)
    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    data = {
        'comment': 'They killed kenny',
        'score': 11,
    }
    response = client.put(url, data)
    json = response.json()

    assert json == {'non_field_errors': ['Score must be between 1 and 10']}
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of('feedback.Answer') == [db]
    assert survey_answered.send_robust.call_args_list == []
    assert activity_tasks.add_activity.delay.call_args_list == []


@pytest.mark.parametrize('score', [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_answer_id_put_with_all_valid_scores(bc: Breathecode, client: APIClient, score):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT'}
    answers = []

    model = bc.database.create(
        user=1,
        answer=True,
        answer_kwargs=answer_kwargs,
    )
    client.force_authenticate(model.user)
    answers.append(model.answer)
    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})

    data = {
        'comment': 'They killed kenny',
        'score': score,
    }
    response = client.put(url, data)
    json = response.json()

    expected = {
        'id': model['answer'].id,
        'title': model['answer'].title,
        'lowest': model['answer'].lowest,
        'highest': model['answer'].highest,
        'lang': model['answer'].lang,
        'score': score,
        'comment': data['comment'],
        'status': 'ANSWERED',
        'opened_at': model['answer'].opened_at,
        'created_at': datetime_to_iso_format(model['answer'].created_at),
        'cohort': model['answer'].cohort,
        'academy': model['answer'].academy,
        'survey': None,
        'mentorship_session': None,
        'sent_at': None,
        'mentor': model['answer'].mentor.id,
        'event': model['answer'].event,
        'user': model['answer'].user.id,
    }

    del json['updated_at']

    assert json == expected

    dicts = [
        answer for answer in bc.database.list_of('feedback.Answer')
        if not 'updated_at' in answer or isinstance(answer['updated_at'], datetime) and answer.pop('updated_at')
    ]

    assert response.status_code == status.HTTP_200_OK

    db['score'] = score
    db['status'] = 'ANSWERED'
    db['comment'] = data['comment']

    assert dicts == [db]

    assert survey_answered.send_robust.call_args_list == [
        call(instance=model.answer, sender=model.answer.__class__),
    ]
    assert activity_tasks.add_activity.delay.call_args_list == [
        call(model.user.id, 'nps_answered', related_type='feedback.Answer', related_id=model.answer.id),
    ]


# # TODO: this test should return 400 but its returning 200, why? If needs to return 400 because you cannot change your score in the answer once you already answered
# def test_answer_id_put_twice_different_score(bc:Breathecode, client:Client):
#     """Test /answer/:id without auth"""
#     model = bc.database.create(user=1,
#                                  answer=True,
#
#                                  answer_score=7,
#                                  answer_status='SENT')
#     db = bc.format.to_dict(model.answer)
#     url = reverse_lazy('feedback:user_me_answer_id',
#                        kwargs={'answer_id': model['answer'].id})
#     data = {
#         'comment': 'They killed kenny',
#         'score': 1,
#     }
#     client.put(url, data)

#     response = client.put(url, data)
#     json = response.json()

#     # assert False
#     assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_answer_id_put_twice_same_score(bc: Breathecode, client: APIClient):
    """Test /answer/:id without auth"""
    answer_kwargs = {'status': 'SENT', 'score': 3}
    model = bc.database.create(user=1, answer=True, answer_kwargs=answer_kwargs)
    client.force_authenticate(model.user)

    db = bc.format.to_dict(model.answer)
    url = reverse_lazy('feedback:user_me_answer_id', kwargs={'answer_id': model['answer'].id})
    data = {
        'comment': 'They killed kenny',
        'score': 3,
    }
    client.put(url, data)
    response = client.put(url, data)
    json = response.json()

    assert response.status_code == status.HTTP_200_OK

    db['score'] = data['score']
    db['status'] = 'ANSWERED'
    db['comment'] = data['comment']

    assert bc.database.list_of('feedback.Answer') == [db]
    assert survey_answered.send_robust.call_args_list == [call(instance=model.answer, sender=model.answer.__class__)]
    assert activity_tasks.add_activity.delay.call_args_list == [
        call(1, 'nps_answered', related_type='feedback.Answer', related_id=1),
        call(1, 'nps_answered', related_type='feedback.Answer', related_id=1),
    ]
