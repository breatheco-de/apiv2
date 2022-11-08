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
            'secondary': [venezuela],
        },
    },
    {
        'code': 'VES',
        'name': 'Bolívar',
        'countries': {
            'main': [venezuela],
            'secondary': [],
        },
    },
    {
        'code': 'UYU',
        'name': 'Peso uruguayo',
        'countries': {
            'main': [uruguay],
            'secondary': [],
        },
    },
    {
        'code': 'EUR',
        'name': 'Euro',
        'countries': {
            'main': [spain],
            'secondary': [],
        },
    },
    {
        'code': 'CRC',
        'name': 'colón costarricense',
        'countries': {
            'main': [costa_rica],
            'secondary': [],
        },
    },
    {
        'code': 'CLP',
        'name': 'peso chileno',
        'countries': {
            'main': [chile],
            'secondary': [],
        },
    },
    {
        'code': 'CAD',
        'name': 'Canadian dollar',
        'countries': {
            'main': [canada],
            'secondary': [],
        },
    },
]


class Command(BaseCommand):
    help = 'Set currencies'

    def handle(self, *args, **options):
        academies_cleaned = set()
        for currency in currencies:
            c, _ = Currency.objects.get_or_create(code=currency['code'], name=currency['name'])
            for country in currency['countries']['main']:
                Academy.objects.filter(country__code=country['code'],
                                       country__name=country['name']).update(main_currency=c)

            for country in currency['countries']['secondary']:
                academies = Academy.objects.filter(country__code=country['code'],
                                                   country__name=country['name'])

                for academy in academies:
                    if academy.id not in academies_cleaned:
                        academy.allowed_currencies.clear()
                        academies_cleaned.add(academy.id)

                    academy.allowed_currencies.filter()
