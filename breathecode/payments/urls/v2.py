from django.urls import path
from .v1 import urlpatterns as urlpatterns_v1

from ..views import (
    V2CardView,
    SubscriptionBillingTeamView,
    SubscriptionSeatView,
)

deprecation_list = [
    "card",
]

app_name = "payments"
urlpatterns = [
    path("card", V2CardView.as_view(), name="card"),
    # Team member endpoints (moved from v1)
    path(
        "subscription/<int:subscription_id>/billing-team",
        SubscriptionBillingTeamView.as_view(),
        name="subscription_id_billing_team",
    ),
    path(
        "subscription/<int:subscription_id>/billing-team/invite",
        SubscriptionBillingTeamView.as_view(),
        name="subscription_id_billing_team_invite",
    ),
    path(
        "subscription/<int:subscription_id>/billing-team/seat",
        SubscriptionSeatView.as_view(),
        name="subscription_id_billing_team_seat",
    ),
    path(
        "subscription/<int:subscription_id>/billing-team/seat/<int:seat_id>",
        SubscriptionSeatView.as_view(),
        name="subscription_id_billing_team_seat_id",
    ),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
