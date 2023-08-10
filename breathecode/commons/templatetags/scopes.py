# my_inclusion_tag.py
from django import template

register = template.Library()


@register.inclusion_tag('scopes.html')
def scopes(*, scopes=[], id='unnamed', title='Unnamed', disabled=False, selected_scopes=[], new_scopes=[]):
    return {
        'scopes': scopes,
        'id': id,
        'title': title,
        'disabled': disabled,
        'selected_scopes': selected_scopes,
        'new_scopes': new_scopes,
    }
