"""
Collections of mixins used to login in authorize microservice
"""


class ModelsMixin():
    """Mixins for models"""
    def remove_dinamics_fields(self,
                               dict,
                               fields=[
                                   '_state', 'created_at', 'updated_at',
                                   '_password'
                               ]):
        """Remove dinamics fields from django models as dict"""
        if not dict:
            return None

        result = dict.copy()
        for field in fields:
            if field in result:
                del result[field]

        return result

    def model_to_dict(self, models: dict, key: str) -> dict:
        """Convert one django models to dict"""
        if key in models:
            return self.remove_dinamics_fields(models[key].__dict__)

    def all_model_dict(self, models: list[dict], sort_by='id') -> list[dict]:
        """Convert all django models to dict"""
        if models:
            models.sort(key=lambda x: getattr(x, sort_by))

        return [
            self.remove_dinamics_fields(data.__dict__.copy())
            for data in models
        ]

    def print_model(self, models: list[dict], key: str, prefix=''):
        print(prefix, f'Current model key: {key}')
        print(prefix, f'Current model data:', models[key].__dict__)
        print('')

    def print_all_models(self, models: list[dict], prefix=''):
        print(prefix, 'Starting to print models in dict format')

        for key in models:
            self.print_model(models, key, prefix)

        print(prefix, 'Ending to print models in dict format')
