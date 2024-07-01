from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest

from breathecode.notify import tasks
from breathecode.notify.utils.hook_manager import HookManager
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def mocks(db, monkeypatch):
    m1 = MagicMock()
    monkeypatch.setattr(tasks.async_deliver_hook, 'delay', m1)
    yield m1


def get_model_label(instance):
    if instance is None:
        return None
    opts = instance._meta.concrete_model._meta
    try:
        return opts.label
    except AttributeError:
        return '.'.join([opts.app_label, opts.object_name])


def test_transform_timedeltas(bc: Breathecode, enable_signals, enable_hook_manager, mocks):
    enable_hook_manager()
    mock = mocks

    model = bc.database.create(hook={'event': 'survey.created'},
                               user={
                                   'username': 'test',
                                   'is_superuser': True
                               },
                               academy={
                                   'slug': 'test',
                                   'available_as_saas': True,
                               },
                               survey=1)

    x = {'feedback.Survey': {'created': ('survey.created', False)}}
    HookManager.HOOK_EVENTS = {'survey.created': 'feedback.Survey.created+'}
    # HookManager._HOOK_EVENT_ACTIONS_CONFIG = x
    HookManager._HOOK_EVENT_ACTIONS_CONFIG = None

    HookManager.process_model_event(
        model.survey,
        get_model_label(model.survey.__class__),
        'created',
        payload_override={
            'delta': timedelta(days=3),
            'children': [
                {
                    'delta': timedelta(days=4)
                },
                {
                    'delta': timedelta(days=5)
                },
            ]
        },
    )

    assert bc.database.list_of('feedback.Survey') == [bc.format.to_dict(model.survey)]

    assert mock.call_args_list == [
        call(model.hook.target, {
            'delta': 259200.0,
            'children': [
                {
                    'delta': 345600.0
                },
                {
                    'delta': 432000.0
                },
            ]
        },
             hook_id=1),
    ]
