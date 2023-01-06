import serpy

from breathecode.utils.validation_exception import ValidationException
from .field import Field
from .method_field import MethodField

__all__ = ['Serializer']


class Serializer(serpy.Serializer):
    """
    This is a wrapper of serpy.Serializer, read the serpy's documentation.

    Extra features:
    - `select` is a list of non-required fields.
    """

    def _custom_select(self, include):
        include = [x for x in include.split(',') if x]
        print('here2')

        for include_field in include:
            if not hasattr(self, include_field):
                raise ValidationException(f'The field {include_field} is not defined in the serializer')

            attr = getattr(self, include_field)
            if isinstance(attr, Field):
                setattr(self, include_field, serpy.Field())
                print('here3')
                continue

            method_field = f'get_{include_field}'

            if isinstance(attr, MethodField) and hasattr(self, method_field) and callable(
                    getattr(self, method_field)):
                setattr(self, include_field, serpy.MethodField())
                print('here4')
                continue

            raise ValidationException(
                f'The field {include_field} is not a allowed field or is bad configured')

    def __init__(self, *args, **kwargs):
        select = kwargs.pop('select', '')
        if select:
            print('here1')
            self._custom_select(select)

        if 'context' in kwargs:
            self.context = kwargs['context']

        super().__init__(*args, **kwargs)
