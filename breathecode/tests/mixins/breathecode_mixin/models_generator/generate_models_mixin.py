"""
Collections of mixins used to login in authorize microservice
"""

from django.db.models import Model
from breathecode.utils import AttrDict

__all__ = ["GenerateModelsMixin"]


class GenerateModelsMixin:

    def __detect_invalid_arguments__(self, models={}, **kwargs):
        """check if one argument is invalid to prevent errors"""
        for key in kwargs:
            if key != "authenticate" and not key.endswith("_kwargs") and not key in models:
                print(f"key `{key}` should not be implemented in self.generate_models")

    def __inject_models_in_instance__(self, models={}):
        """Add support to model.name instead of model['name']"""
        models = models.copy()
        return AttrDict(**models)

    def __flow_wrapper__(self, *args, **kwargs):
        models = {}

        if "models" in kwargs:
            models = kwargs["models"].copy()
            del kwargs["models"]

        for func in args:
            models = func(models=models, **kwargs)

        self.__detect_invalid_arguments__(models, **kwargs)
        models = self.__inject_models_in_instance__(models)

        return models

    def __flow__(self, *args):

        def inner_wrapper(**kwargs):
            return self.__flow_wrapper__(*args, **kwargs)

        return inner_wrapper

    def __inject_models__(self, models={}, **kwargs):
        """Allow pass models passed in args instead of name=True"""
        models = models.copy()

        for key in kwargs:
            kwarg = kwargs[key]
            if isinstance(kwarg, Model):
                models[key] = kwarg

        return models

    def generate_models(self, models={}, **kwargs):
        if "_new_implementation" not in kwargs:
            print(f"The method `generate_models` is deprecated, use `self.bc.database.create` instead")

        else:
            del kwargs["_new_implementation"]

        if "authenticate" in kwargs:
            print(f"The argument `authenticate` is deprecated, use `self.bc.request.authenticate` instead")

        self.maxDiff = None
        models = models.copy()
        models = self.__inject_models__(models, **kwargs)
