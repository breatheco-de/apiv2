"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class MarketingModelsMixin(ModelsMixin):
    def generate_marketing_models(self,
                                  active_campaign_academy=False,
                                  automation=False,
                                  academy=False,
                                  tag=False,
                                  contact=False,
                                  form_entry=False,
                                  short_link=False,
                                  user=False,
                                  active_campaign_academy_kwargs={},
                                  automation_kwargs={},
                                  tag_kwargs={},
                                  contact_kwargs={},
                                  form_entry_kwargs={},
                                  short_link_kwargs={},
                                  models={},
                                  **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'active_campaign_academy' in models and active_campaign_academy:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **active_campaign_academy_kwargs}
            models['active_campaign_academy'] = mixer.blend(
                'marketing.ActiveCampaignAcademy', **kargs)

        if not 'automation' in models and automation:
            kargs = {}

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            kargs = {**kargs, **automation_kwargs}
            models['automation'] = mixer.blend('marketing.Automation', **kargs)

        # OneToOneField
        if 'active_campaign_academy' in models and active_campaign_academy:
            if 'automation' in models or automation:
                models[
                    'active_campaign_academy'].event_attendancy_automation = models[
                        'automation']

            models['active_campaign_academy'].save()

        if not 'tag' in models and tag:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            kargs = {**kargs, **tag_kwargs}
            models['tag'] = mixer.blend('marketing.Tag', **kargs)

        if not 'contact' in models and contact:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **contact_kwargs}
            models['contact'] = mixer.blend('marketing.Contact', **kargs)

        if not 'form_entry' in models and form_entry:
            kargs = {}

            if 'contact' in models or contact:
                kargs['contact'] = models['contact']

            if 'tag' in models or tag:
                kargs['tag_objects'] = [models['tag']]

            if 'automation' in models or automation:
                kargs['automation_objects'] = [models['automation']]

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'active_campaign_academy' in models or active_campaign_academy:
                kargs['ac_academy'] = models['active_campaign_academy']

            kargs = {**kargs, **form_entry_kwargs}
            models['form_entry'] = mixer.blend('marketing.FormEntry', **kargs)

        if not 'short_link' in models and short_link:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'user' in models or user:
                kargs['author'] = models['user']

            kargs = {**kargs, **short_link_kwargs}
            models['short_link'] = mixer.blend('marketing.ShortLink', **kargs)

        return models
