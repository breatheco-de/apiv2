"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class JobsModelsMixin(ModelsMixin):
    def generate_jobs_models(self,
                             platform=False,
                             position=False,
                             zyte_project=False,
                             spider=False,
                             position_alias=False,
                             tag=False,
                             location=False,
                             location_alias=False,
                             employer=False,
                             job=False,
                             platform_kwargs={},
                             position_kwargs={},
                             zyte_project_kwargs={},
                             spider_kwargs={},
                             position_alias_kwargs={},
                             tag_kwargs={},
                             location_kwargs={},
                             location_alias_kwargs={},
                             employer_kwargs={},
                             job_kwargs={},
                             models={},
                             **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'platform' in models and platform:
            kargs = {}

            kargs = {**kargs, **platform_kwargs}
            models['platform'] = mixer.blend('jobs.Platform', **kargs)

        if not 'position' in models and (position or spider):
            kargs = {}

            kargs = {**kargs, **position_kwargs}
            models['position'] = mixer.blend('jobs.Position', **kargs)

        if not 'zyte_project' in models and (zyte_project or spider):
            kargs = {}

            if 'platform' in models or platform:
                kargs['platform'] = models['platform']

            kargs = {**kargs, **zyte_project_kwargs}
            models['zyte_project'] = mixer.blend('jobs.ZyteProject', **kargs)

        if not 'spider' in models and spider:
            kargs = {}

            if 'position' in models or position:
                kargs['position'] = models['position']

            if 'zyte_project' in models or zyte_project:
                kargs['zyte_project'] = models['zyte_project']

            kargs = {**kargs, **spider_kwargs}
            models['spider'] = mixer.blend('jobs.Spider', **kargs)

        if not 'position_alias' in models and position_alias:
            kargs = {}

            if 'position' in models or position:
                kargs['position'] = models['position']

            kargs = {**kargs, **position_alias_kwargs}
            models['position_alias'] = mixer.blend('jobs.PositionAlias', **kargs)

        if not 'tag' in models and tag:
            kargs = {}

            kargs = {**kargs, **tag_kwargs}
            models['tag'] = mixer.blend('jobs.Tag', **kargs)

        if not 'location' in models and location:
            kargs = {}

            kargs = {**kargs, **location_kwargs}
            models['location'] = mixer.blend('jobs.Location', **kargs)

        if not 'location_alias' in models and location_alias:
            kargs = {}

            if 'location' in models or location:
                kargs['location'] = models['location']

            kargs = {**kargs, **location_alias_kwargs}
            models['location_alias'] = mixer.blend('jobs.LocationAlias', **kargs)

        if not 'employer' in models and employer:
            kargs = {}

            if 'location' in models or location:
                kargs['location'] = models['location']

            kargs = {**kargs, **employer_kwargs}
            models['employer'] = mixer.blend('jobs.Employer', **kargs)

        if not 'job' in models and (job or employer):
            kargs = {}

            if 'platform' in models or platform:
                kargs['platform'] = models['platform']

            if 'employer' in models or employer:
                kargs['employer'] = models['employer']

            if 'position' in models or position:
                kargs['position'] = models['position']

            if 'tag' in models or tag:
                kargs['tag'] = [models['tag']]

            if 'location' in models or location:
                kargs['locations'] = [models['location']]

            kargs = {**kargs, **job_kwargs}
            models['job'] = mixer.blend('jobs.Job', **kargs)

        return models
