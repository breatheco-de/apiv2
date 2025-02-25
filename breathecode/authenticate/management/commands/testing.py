import aiohttp
import os

# import requests
# import json
from django.core.management.base import BaseCommand
from ...models import CredentialsGoogle


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    async def handle(self, *args, **options):
        print("HI!!!")
        # credentials = CredentialsGoogle.objects.filter(user__id=13).first()
        # token = credentials.token
        # print("token")
        # print(token)
        print("CODE!!!")
        code = 200

        payload = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URL", ""),
            "grant_type": "authorization_code",
            "code": code,
        }
        headers = {"Accept": "application/json"}
        print("HEADERS!!!")
        async with aiohttp.ClientSession() as session:
            async with session.post("https://oauth2.googleapis.com/token", json=payload, headers=headers) as resp:
                print("POST!!!!")
                print(resp)
                google_id = 103672766563745367276

                google_creds = await CredentialsGoogle.objects.filter(google_id=google_id).afirst()
                print("REQUEST DONE!!!")
                if google_creds:
                    user = google_creds.user
                    print("user")
                    print(user)

        # url = "https://www.googleapis.com/oauth2/v2/userinfo?alt=json"
        # headers = {"Authorization": f"Bearer {token}"}
        # print("headers")
        # print(headers)
        # res = requests.get(url, headers=headers)
        # res = json.loads(res.text)
        # print("AAAAAAAAAAAA")
        # print(res)
