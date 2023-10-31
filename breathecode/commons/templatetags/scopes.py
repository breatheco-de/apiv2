# my_inclusion_tag.py
from django import template

register = template.Library()


@register.inclusion_tag('scopes.html')
def scopes(*,
           scopes=None,
           id='unnamed',
           title='Unnamed',
           disabled=False,
           selected_scopes=None,
           new_scopes=None):

    if scopes is None:
        scopes = []

    if selected_scopes is None:
        selected_scopes = []

    if new_scopes is None:
        new_scopes = []

    return {
        'scopes': scopes,
        'id': id,
        'title': title,
        'disabled': disabled,
        'selected_scopes': selected_scopes,
        'new_scopes': new_scopes,
    }
