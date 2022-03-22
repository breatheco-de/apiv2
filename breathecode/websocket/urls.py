from django.urls import path

from . import consumers

# here is the router of websocket
websocket_urlpatterns = [
    path('ws/online/cohort/<str:cohort_slug>/', consumers.OnlineCohortConsumer.as_asgi()),
    path('ws/online/academy/<str:academy_slug>/', consumers.OnlineFromAcademyConsumer.as_asgi()),
]
