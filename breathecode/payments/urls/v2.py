from django.urls import path
from .v1 import urlpatterns as urlpatterns_v1

from ..views import V2CardView, AcademyTeamMemberView, TeamMemberInviteStatusView, AcademySubscriptionSeatView

deprecation_list = [
    "card",
]

app_name = "payments"
urlpatterns = [
    path("card", V2CardView.as_view(), name="card"),
    # Team member endpoints (moved from v1)
    path(
        "academy/subscription/<int:subscription_id>/billing-team",
        AcademyTeamMemberView.as_view(),
        name="academy_subscription_id_billing_team",
    ),
    path(
        "academy/subscription/<int:subscription_id>/billing-team/invite",
        AcademyTeamMemberView.as_view(),
        name="academy_subscription_id_billing_team",
    ),
    path(
        "academy/subscription/<int:subscription_id>/billing-team/seat",
        AcademySubscriptionSeatView.as_view(),
        name="academy_subscription_id_billing_team_seat",
    ),
    path(
        "academy/subscription/<int:subscription_id>/billing-team/seat/<int:seat_id>",
        AcademySubscriptionSeatView.as_view(),
        name="academy_subscription_id_billing_team_seat_id",
    ),
    path(
        "academy/subscription/<int:subscription_id>/billing-team/seat/<int:seat_id>/invite",
        TeamMemberInviteStatusView.as_view(),
        name="academy_subscription_id_billing_team_seat_id",
    ),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
