from django.urls import path
from .v1 import urlpatterns as urlpatterns_v1

from ..views import (
    V2CardView,
    PlanFinancingSeatView,
    PlanFinancingTeamView,
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
        "subscription/<int:subscription_id>/billing-team/seat",
        SubscriptionSeatView.as_view(),
        name="subscription_id_billing_team_seat",
    ),
    path(
        "subscription/<int:subscription_id>/billing-team/seat/<int:seat_id>",
        SubscriptionSeatView.as_view(),
        name="subscription_id_billing_team_seat_id",
    ),
    path(
        "plan-financing/<int:plan_financing_id>/team",
        PlanFinancingTeamView.as_view(),
        name="plan_financing_id_team",
    ),
    path(
        "plan-financing/<int:plan_financing_id>/team/seat",
        PlanFinancingSeatView.as_view(),
        name="plan_financing_id_team_seat",
    ),
    path(
        "plan-financing/<int:plan_financing_id>/team/seat/<int:seat_id>",
        PlanFinancingSeatView.as_view(),
        name="plan_financing_id_team_seat_id",
    ),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
