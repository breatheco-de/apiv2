from functools import cache
from django.db.models.fields.related_descriptors import (ManyToManyDescriptor, ForwardManyToOneDescriptor)


@cache
def load_model_info(model):
    to_one = [x for x in dir(model) if isinstance(getattr(model, x), ForwardManyToOneDescriptor)]
    to_many = [x for x in dir(model) if isinstance(getattr(model, x), ManyToManyDescriptor)]
    return {
        'app_name': model._meta.app_label,
        'model_name': model._meta.object_name,
        'pk': model._meta.pk.name,
        'fields': [f.name for f in model._meta.fields if f.name not in to_one + to_many],
        'relationships': {
            'to_one': to_one,
            'to_many': to_many
        }
    }
