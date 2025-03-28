from django.urls import path

from .views import (
    CertificateAcademyView,
    CertificateCohortView,
    CertificateMeView,
    CertificateView,
    LayoutView,
    get_academy_specialties,
    get_badges,
    get_certificate,
)

app_name = "certificate"
urlpatterns = [
    path("academy/specialty", get_academy_specialties),
    path("badge", get_badges),
    path("academy/layout", LayoutView.as_view()),
    path("token/<str:token>/", get_certificate),
    path("cohort/<int:cohort_id>/student/<int:student_id>", CertificateView.as_view(), name="cohort_id_student_id"),
    path("cohort/<int:cohort_id>", CertificateCohortView.as_view(), name="cohort_id"),
    path("", CertificateAcademyView.as_view(), name="root"),
    path("me", CertificateMeView.as_view(), name="me"),
]
