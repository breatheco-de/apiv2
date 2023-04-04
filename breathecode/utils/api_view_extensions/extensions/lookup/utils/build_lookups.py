from functools import cache
import re
from typing import Optional
from breathecode.utils.api_view_extensions.extensions.lookup.utils.get_field import get_field

from breathecode.utils.api_view_extensions.extensions.lookup.utils.load_model_info import load_model_info
from breathecode.utils.api_view_extensions.extensions.lookup.utils.parse_child_field import parse_child_field
from breathecode.utils.api_view_extensions.extensions.lookup.utils.resolve_field_mode import resolve_field_mode


def build_lookups_tree(model,
                       custom_fields: frozenset = frozenset(),
                       alias: frozenset = frozenset(),
                       id: Optional[tuple] = None,
                       exact: Optional[tuple] = None,
                       gt: Optional[tuple] = None,
                       gte: Optional[tuple] = None,
                       lt: Optional[tuple] = None,
                       lte: Optional[tuple] = None,
                       is_null: Optional[tuple] = None,
                       parent: tuple = tuple(),
                       prefix: str = ''):

    info = load_model_info(model)

    # transform from hashable type to dict
    custom_fields = dict(custom_fields)
    alias = dict(alias)

    result = {}

    for name in info['fields']:
        mode = resolve_field_mode(name, id, exact, gt, gte, lt, lte, is_null)

        if mode:
            django_handler = getattr(model, name)
            result[name] = get_field(name, mode, django_handler)

    for name in info['relationships']['to_one']:
        child_model = getattr(model, name).field.related_model
        child = build_lookups_tree(child_model,
                                   custom_fields=frozenset(custom_fields.items()),
                                   alias=frozenset(alias.items()),
                                   id=parse_child_field(name, id),
                                   exact=parse_child_field(name, exact),
                                   gt=parse_child_field(name, gt),
                                   gte=parse_child_field(name, gte),
                                   lt=parse_child_field(name, lt),
                                   lte=parse_child_field(name, lte),
                                   is_null=parse_child_field(name, is_null),
                                   parent=(*parent, model),
                                   prefix=prefix + name + '__')

        result[name] = child

        mode = resolve_field_mode(name, id, exact, gt, gte, lt, lte, is_null)

        if mode:
            django_handler = getattr(model, name)
            result[name]['$instance'] = get_field(name, mode, django_handler)

    return result


def extract_flat_lookups(lookup, prefix: str = ''):
    result = {}

    for key in lookup:
        if isinstance(lookup[key], dict):
            n = extract_flat_lookups(lookup[key], prefix + key + '__')
            instance = n.pop('$instance', None)
            result.update(n)
            if instance:
                k = prefix

                if key == '$instance':
                    p = re.sub(r'__', '@@', k, count=0, flags=0)
                    p = re.sub(r'@@[a-zA-Z_\d]+@@$', '@@', p, count=0, flags=0)
                    p = re.sub(r'@@', '__', p, count=0, flags=0)
                    k = re.sub(r'__$', '', k, count=0, flags=0)

                else:
                    k += key
                    p = prefix

                lookup[key].prefix = p

                result[k] = instance
        else:
            k = prefix

            if key == '$instance':
                p = re.sub(r'__', '@@', k, count=0, flags=0)
                p = re.sub(r'@@[a-zA-Z_\d]+@@$', '@@', p, count=0, flags=0)
                p = re.sub(r'@@', '__', p, count=0, flags=0)
                k = re.sub(r'__$', '', k, count=0, flags=0)

            else:
                k += key
                p = prefix

            lookup[key].prefix = p

            result[k] = lookup[key]

    return result


@cache
def build_lookups(model,
                  custom_fields: frozenset = frozenset(),
                  alias: frozenset = frozenset(),
                  id: Optional[tuple] = None,
                  exact: Optional[tuple] = None,
                  gt: Optional[tuple] = None,
                  gte: Optional[tuple] = None,
                  lt: Optional[tuple] = None,
                  lte: Optional[tuple] = None,
                  is_null: Optional[tuple] = None,
                  parent: tuple = tuple(),
                  prefix: str = ''):

    result = {}
    lookup = build_lookups_tree(model, custom_fields, alias, id, exact, gt, gte, lt, lte, is_null, parent,
                                prefix)

    lookup = extract_flat_lookups(lookup)

    return lookup
