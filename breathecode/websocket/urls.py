from django.urls import path

from . import consumers

# here is the router of websocket
websocket_urlpatterns = [
    path('ws/cohort/<str:cohort_slug>/', consumers.CohortConsumer.as_asgi()),
    path('ws/online', consumers.OnlineStatusConsumer.as_asgi()),
]
