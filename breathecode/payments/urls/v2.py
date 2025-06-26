from django.urls import path
from .v1 import urlpatterns as urlpatterns_v1

from ..views import V2CardView

deprecation_list = [
    "card",
]

app_name = "payments"
urlpatterns = [
    path("card", V2CardView.as_view(), name="card"),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
