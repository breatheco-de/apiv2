# my_inclusion_tag.py
from django import template

register = template.Library()


@register.inclusion_tag('button.html')
def button(*, type='button', href='#', onclick='', className='', value):
    return {
        'type': type,
        'href': href,
        'onclick': onclick,
        'className': className,
        'value': value,
    }
