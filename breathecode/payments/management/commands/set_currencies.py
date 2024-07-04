from django.core.management.base import BaseCommand

from breathecode.admissions.models import Academy
from breathecode.payments.models import Currency

usa = {
    "code": "us",
    "name": "USA",
}

venezuela = {
    "code": "ve",
    "name": "Venezuela",
}

uruguay = {
    "code": "uy",
    "name": "Uruguay",
}

online = {
    "code": "on",
    "name": "Online",
}

spain = {
    "code": "es",
    "name": "Spain",
}

costa_rica = {
    "code": "cr",
    "name": "Costa Rica",
}

chile = {
    "code": "cl",
    "name": "Chile",
}

canada = {
    "code": "ca",
    "name": "Canada",
}

currencies = [
    {
        "code": "USD",
        "name": "United States dollar",
        "decimals": 2,
        "countries": {
            "main": [usa, online, venezuela, uruguay, chile, canada, costa_rica],
        },
    },
    {
        "code": "EUR",
        "name": "Euro",
        "decimals": 2,
        "countries": {
            "main": [spain],
        },
    },
    {
        "code": "CLP",
        "name": "peso chileno",
        "decimals": 0,
        "countries": {
            "main": [chile],
        },
    },
]


class Command(BaseCommand):
    help = "Set currencies"

    def handle(self, *args, **options):
        for currency in currencies:
            c, _ = Currency.objects.get_or_create(
                code=currency["code"], name=currency["name"], decimals=currency["decimals"]
            )
            for country in currency["countries"]["main"]:
                Academy.objects.filter(country__code=country["code"], country__name=country["name"]).update(
                    main_currency=c
                )
