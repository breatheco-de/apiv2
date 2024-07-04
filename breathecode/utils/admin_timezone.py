from django.utils import timezone
import pytz, os

__all__ = ["TimezoneMiddleware"]

ENV = os.getenv("ENV", None)


class TimezoneMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if ENV != "test":
            timezone.activate(pytz.timezone("America/New_York"))
        return self.get_response(request)
