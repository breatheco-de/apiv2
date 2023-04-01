from functools import cache
from typing import Optional
from breathecode.utils.api_view_extensions.extensions.lookup.utils.get_field import get_field

from breathecode.utils.api_view_extensions.extensions.lookup.utils.load_model_info import load_model_info
from breathecode.utils.api_view_extensions.extensions.lookup.utils.parse_child_field import parse_child_field
from breathecode.utils.api_view_extensions.extensions.lookup.utils.resolve_field_mode import resolve_field_mode


@cache
def build_lookups(
        model,
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
):

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

        child = build_lookups(getattr(model, name).field.related_model,
                              custom_fields=frozenset(custom_fields.items()),
                              alias=frozenset(alias.items()),
                              id=parse_child_field(name, id),
                              exact=parse_child_field(name, exact),
                              gt=parse_child_field(name, gt),
                              gte=parse_child_field(name, gte),
                              lt=parse_child_field(name, lt),
                              lte=parse_child_field(name, lte),
                              is_null=parse_child_field(name, is_null),
                              parent=(*parent, model))

        mode = resolve_field_mode(name, id, exact, gt, gte, lt, lte, is_null)

        if mode:
            django_handler = getattr(model, name)
            result[name] = get_field(name, mode, django_handler)

        for key in child:
            child[key].set_lookup()

            if not child[key].prefix.startswith(f'{name}__'):
                child[key].append_prefix(f'{name}__')

            child[key].prefix + child[key].lookup
            result[child[key].prefix + child[key].lookup] = child[key]

    return result
