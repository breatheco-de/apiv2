import requests
import json
from django.core.management.base import BaseCommand
from ...models import CredentialsGoogle


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    def handle(self, *args, **options):
        credentials = CredentialsGoogle.objects.filter(user__id=13).first()
        token = credentials.token
        print("token")
        print(token)

        url = "https://www.googleapis.com/oauth2/v2/userinfo?alt=json"
        headers = {"Authorization": f"Bearer {token}"}
        print("headers")
        print(headers)
        res = requests.get(url, headers=headers)
        res = json.loads(res.text)
        print("AAAAAAAAAAAA")
        print(res)
