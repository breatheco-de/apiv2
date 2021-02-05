"""
Collections of mixins used to login in authorize microservice
"""

class ModelsMixin():
    """Mixins for models"""

    def remove_dinamics_fields(self, dict):
        """Remove dinamics fields from django models as dict"""
        fields = ['_state', 'created_at', 'updated_at']

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

    def all_model_dict(self, models: list[dict]):
        """Convert all django models to dict"""
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in models]
