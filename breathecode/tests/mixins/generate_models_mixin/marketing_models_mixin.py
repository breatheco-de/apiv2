"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


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
                                  academy_alias=False,
                                  active_campaign_academy_kwargs={},
                                  automation_kwargs={},
                                  tag_kwargs={},
                                  academy_alias_kwargs={},
                                  contact_kwargs={},
                                  form_entry_kwargs={},
                                  short_link_kwargs={},
                                  models={},
                                  **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'active_campaign_academy' in models and is_valid(active_campaign_academy):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = just_one(models['academy'])

            models['active_campaign_academy'] = create_models(active_campaign_academy,
                                                              'marketing.ActiveCampaignAcademy', **{
                                                                  **kargs,
                                                                  **active_campaign_academy_kwargs
                                                              })

        if not 'automation' in models and is_valid(automation):
            kargs = {}

            if 'active_campaign_academy' in models:
                kargs['ac_academy'] = just_one(models['active_campaign_academy'])

            models['automation'] = create_models(automation, 'marketing.Automation', **{
                **kargs,
                **automation_kwargs
            })

        if not 'academy_alias' in models and is_valid(academy_alias):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['academy_alias'] = create_models(academy_alias, 'marketing.AcademyAlias', **{
                **kargs,
                **academy_alias_kwargs
            })

        # OneToOneField
        if 'active_campaign_academy' in models and is_valid(active_campaign_academy):
            if 'automation' in models:
                models['active_campaign_academy'].event_attendancy_automation = just_one(models['automation'])

            models['active_campaign_academy'].save()

        if not 'tag' in models and is_valid(tag):
            kargs = {}

            if 'active_campaign_academy' in models:
                kargs['ac_academy'] = just_one(models['active_campaign_academy'])

            if 'automation' in models:
                kargs['automation'] = just_one(models['automation'])

            models['tag'] = create_models(tag, 'marketing.Tag', **{**kargs, **tag_kwargs})

        if not 'contact' in models and is_valid(contact):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['contact'] = create_models(contact, 'marketing.Contact', **{**kargs, **contact_kwargs})

        if not 'form_entry' in models and is_valid(form_entry):
            kargs = {}

            if 'contact' in models:
                kargs['contact'] = just_one(models['contact'])

            if 'tag' in models:
                kargs['tag_objects'] = get_list(models['tag'])

            if 'automation' in models:
                kargs['automation_objects'] = get_list(models['automation'])

            if 'academy' in models or academy:
                kargs['academy'] = just_one(models['academy'])

            if 'active_campaign_academy' in models:
                kargs['ac_academy'] = just_one(models['active_campaign_academy'])

            models['form_entry'] = create_models(form_entry, 'marketing.FormEntry', **{
                **kargs,
                **form_entry_kwargs
            })

        if not 'short_link' in models and is_valid(short_link):
            kargs = {}

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            if 'user' in models:
                kargs['author'] = just_one(models['user'])

            models['short_link'] = create_models(short_link, 'marketing.ShortLink', **{
                **kargs,
                **short_link_kwargs
            })

        return models
