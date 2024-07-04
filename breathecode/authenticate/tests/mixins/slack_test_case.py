"""
Collections of mixins used to login in authorize microservice
"""

import base64
import urllib
from django.urls.base import reverse_lazy
from rest_framework.test import APITestCase
from mixer.backend.django import mixer


# class SlackTestCase(APITestCase, DevelopmentEnvironment):
class SlackTestCase(APITestCase):
    """APITestCase with Slack methods"""

    url_callback = "https://google.co.ve"
    academy = None

    def slack(self):
        """Get /slack"""
        url = reverse_lazy("authenticate:slack")
        params = {"url": base64.b64encode(self.url_callback.encode("utf-8")), "user": 1, "a": self.academy}
        return self.client.get(f"{url}?{urllib.parse.urlencode(params)}")

    def get_academy(self):
        """Generate a academy with mixer"""
        academy = mixer.blend("admissions.Academy")
        self.academy = academy
