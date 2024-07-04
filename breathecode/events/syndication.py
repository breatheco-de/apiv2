import os
from django.contrib.syndication.views import Feed
from django.utils import timezone
from .models import Event  # Assuming Event is the name of your model


class LatestEventsFeed(Feed):
    title = "Latest Events Feed"
    link = "/feeds/latest-events/"  # Update to your desired link
    description = "Feed of the latest events based on provided filters."

    def get_object(self, request, *args, **kwargs):
        lookup = {}

        # All the query filtering you provided goes here...
        # Note: I'm directly using the code you provided to build the lookup dictionary.

        if "city" in request.GET:
            city = request.GET.get("city")
            lookup["venue__city__iexact"] = city

        if "country" in request.GET:
            value = request.GET.get("country")
            lookup["venue__country__iexact"] = value

        if "type" in request.GET:
            value = request.GET.get("type")
            lookup["event_type__slug"] = value

        if "zip_code" in request.GET:
            value = request.GET.get("zip_code")
            lookup["venue__zip_code"] = value

        if "academy" in request.GET:
            value = request.GET.get("academy")
            lookup["academy__slug__in"] = value.split(",")

        if "academy_id" in request.GET:
            value = request.GET.get("academy_id")
            lookup["academy__id__in"] = value.split(",")

        if "lang" in request.GET:
            value = request.GET.get("lang")
            lookup["lang"] = value.split(",")

        if "status" in request.GET:
            value = request.GET.get("status")
            lookup["status__in"] = value.split(",")
        else:
            lookup["status"] = "ACTIVE"

        online_event = request.GET.get("online_event", None)
        if online_event == "true":
            lookup["online_event"] = True
        elif online_event == "false":
            lookup["online_event"] = False

        # upcoming by default
        lookup["ending_at__gte"] = timezone.now()
        if "past" in request.GET:
            if request.GET.get("past") == "true":
                lookup.pop("ending_at__gte")
                lookup["starting_at__lte"] = timezone.now()

        items = Event.objects.filter(**lookup).order_by("starting_at")
        return items

    def items(self, obj):
        # The obj here will be the filtered queryset you returned from get_object
        return obj

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_link(self, item):

        basename = item.academy.white_label_url
        if basename is None or basename == "":
            basename = os.getenv("APP_URL", "")

        lang = "" if item.lang in ["us", "en"] else f"{item.lang}/"
        return f"{basename}/{lang}workshops/{item.slug}"
