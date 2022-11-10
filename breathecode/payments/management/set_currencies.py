from django.core.management.base import BaseCommand

from breathecode.admissions.models import Academy
from breathecode.payments.models import Currency

usa = {
    'code': 'us',
    'name': 'USA',
}

venezuela = {
    'code': 've',
    'name': 'Venezuela',
}

uruguay = {
    'code': 'uy',
    'name': 'Uruguay',
}

online = {
    'code': 'on',
    'name': 'Online',
}

spain = {
    'code': 'es',
    'name': 'Spain',
}

costa_rica = {
    'code': 'cr',
    'name': 'Costa Rica',
}

chile = {
    'code': 'cl',
    'name': 'Chile',
}

canada = {
    'code': 'ca',
    'name': 'Canada',
}

currencies = [
    {
        'code': 'USD',
        'name': 'United States dollar',
        'countries': {
            'main': [usa, online],
        },
    },
    {
        'code': 'VES',
        'name': 'Bolívar',
        'countries': {
            'main': [venezuela],
        },
    },
    {
        'code': 'UYU',
        'name': 'Peso uruguayo',
        'countries': {
            'main': [uruguay],
        },
    },
    {
        'code': 'EUR',
        'name': 'Euro',
        'countries': {
            'main': [spain],
        },
    },
    {
        'code': 'CRC',
        'name': 'colón costarricense',
        'countries': {
            'main': [costa_rica],
        },
    },
    {
        'code': 'CLP',
        'name': 'peso chileno',
        'countries': {
            'main': [chile],
        },
    },
    {
        'code': 'CAD',
        'name': 'Canadian dollar',
        'countries': {
            'main': [canada],
        },
    },
]


class Command(BaseCommand):
    help = 'Set currencies'

    def handle(self, *args, **options):
        for currency in currencies:
            c, _ = Currency.objects.get_or_create(code=currency['code'], name=currency['name'])
            for country in currency['countries']['main']:
                Academy.objects.filter(country__code=country['code'],
                                       country__name=country['name']).update(main_currency=c)
