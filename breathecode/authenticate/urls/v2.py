from django.urls import path

from ..views import V2AppAcademyView, V2AppCityView, V2AppCountryView, V2AppStudentView, V2AppUserView
from .v1 import urlpatterns as urlpatterns_v1

deprecation_list = [
    "app/user",
    "app/user/<int:user_id>",
]

app_name = "authenticate"
urlpatterns = [
    path("app/user", V2AppUserView.as_view(), name="app_user"),
    path("app/user/<int:user_id>", V2AppUserView.as_view(), name="app_user_id"),
    path("app/student", V2AppStudentView.as_view(), name="app_student"),
    path("app/student/<str:user_id_or_email>", V2AppStudentView.as_view(), name="app_student_id"),
    path("app/academy", V2AppAcademyView.as_view(), name="app_academy"),
    path("app/academy/<int:academy_id>", V2AppAcademyView.as_view(), name="app_academy_id"),
    path("app/city", V2AppCityView.as_view(), name="app_city"),
    path("app/city/<int:city_id>", V2AppCityView.as_view(), name="app_city_id"),
    path("app/country", V2AppCountryView.as_view(), name="app_country"),
    path("app/country/<int:country_id>", V2AppCountryView.as_view(), name="app_country_id"),
    *[r for r in urlpatterns_v1 if r.pattern._route not in deprecation_list],
]
