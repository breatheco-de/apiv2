# my_inclusion_tag.py
from django import template

register = template.Library()


@register.inclusion_tag('scopes.html')
def scopes(*, scopes=[], id='unnamed', title='Unnamed', disabled=False):
    return {
        'scopes': scopes,
        'id': id,
        'title': title,
        'disabled': disabled,
    }
