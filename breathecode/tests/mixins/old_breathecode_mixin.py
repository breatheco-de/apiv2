"""
Cache mixin
"""
from breathecode.tests.mocks import OLD_BREATHECODE_INSTANCES
from unittest.mock import call
from breathecode.services import SOURCE, CAMPAIGN


class OldBreathecodeMixin():
    """Cache mixin"""
    old_breathecode_host = 'https://old.hardcoded.breathecode.url'
    OLD_BREATHECODE_TYPES = ['create_contact', 'contact_automations']

    def __create_contact_call__(self, model):
        event = model['event']
        data = {
            'email': model['user'].email,
            'first_name': model['user'].first_name,
            'last_name': model['user'].last_name,
            'field[18,0]': model['academy'].slug,
            'field[34,0]': SOURCE,
            'field[33,0]': CAMPAIGN,
        }

        if event and event.lang:
            data['field[16,0]'] = event.lang

        return call('POST',
                    f'{self.old_breathecode_host}/admin/api.php',
                    params=[('api_action', 'contact_sync'),
                            ('api_key',
                             model['active_campaign_academy'].ac_key),
                            ('api_output', 'json')],
                    data=data)

    def __contact_automations_call__(self, model):
        return call('POST',
                    f'{self.old_breathecode_host}/api/3/contactAutomations',
                    headers={
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'Api-Token': model['active_campaign_academy'].ac_key,
                    },
                    json={
                        'contactAutomation': {
                            'contact': 1,
                            'automation': model['automation'].acp_id,
                        }
                    })

    def reset_old_breathecode_calls(self):
        mock = OLD_BREATHECODE_INSTANCES['request']
        mock.call_args_list = []

    def check_old_breathecode_calls(self, model, types):
        mock = OLD_BREATHECODE_INSTANCES['request']

        calls = []
        for type in types:
            method = getattr(self, f'__{type}_call__')

            if not method:
                raise Exception(f'Type {type} is not implemented')

            calls.append(method(model))

        self.assertEqual(mock.call_args_list, calls)
