"""breathecode URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from graphene_django.views import GraphQLView

from breathecode.utils.urls import mount_app_openapi
from breathecode.utils.views import get_root_schema_view

ENVIRONMENT = os.environ.get("ENV")

versions = {
    "v2": [
        path("activity/", include("breathecode.activity.urls.v2", namespace="activity")),
        path("registry/", include("breathecode.registry.urls.v2", namespace="registry")),
    ],
}

apps = [
    ("v1/auth/", "breathecode.authenticate.urls", "auth"),
    ("v1/admissions/", "breathecode.admissions.urls", "admissions"),
    ("v1/assignment/", "breathecode.assignments.urls", "assignments"),
    ("v1/freelance/", "breathecode.freelance.urls", "freelance"),
    ("v1/events/", "breathecode.events.urls", "events"),
    ("v1/registry/", "breathecode.registry.urls.v1", "registry"),
    ("v1/activity/", "breathecode.activity.urls.v1", "activity"),
    ("v1/feedback/", "breathecode.feedback.urls", "feedback"),
    ("v1/messaging/", "breathecode.notify.urls", "notify"),
    ("v1/assessment/", "breathecode.assessment.urls", "assessment"),
    ("v1/certificate/", "breathecode.certificate.urls", "certificate"),
    ("v1/media/", "breathecode.media.urls", "media"),
    ("v1/marketing/", "breathecode.marketing.urls", "marketing"),
    ("v1/mentorship/", "breathecode.mentorship.urls", "mentorship"),
    ("v1/monitoring/", "breathecode.monitoring.urls", "monitoring"),
    ("v1/provisioning/", "breathecode.provisioning.urls", "provisioning"),
    ("v1/payments/", "breathecode.payments.urls", "payments"),
    ("s/", "breathecode.marketing.urls_shortner", "marketing_shortner"),
    ("mentor/", "breathecode.mentorship.urls_shortner", "mentorship_shortner"),
    ("asset/", "breathecode.registry.urls_shortner", "registry_shortner"),
    ("start", "breathecode.provisioning.urls_shortner", "provisioning_shortner"),
]

urlpatterns_apps = [path(url, include(urlconf, namespace=namespace)) for url, urlconf, namespace in apps]

urlpatterns_app_openapi = [mount_app_openapi(url, urlconf, namespace) for url, urlconf, namespace in apps]

urlpatterns_docs = [
    path(
        "openapi.json",
        get_root_schema_view(
            [namespace for _, _, namespace in apps if namespace != "shortner"],
            extend={
                "title": "4Geeks API",
                "description": "Technology for Learning",
                "version": "v1.0.0",
            },
        ),
        name="openapi-schema",
    ),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path(
        "swagger/",
        TemplateView.as_view(template_name="swagger-ui.html", extra_context={"schema_url": "openapi-schema"}),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        TemplateView.as_view(template_name="redoc.html", extra_context={"schema_url": "openapi-schema"}),
        name="redoc",
    ),
]

urlpatterns_django = [
    path("admin/", admin.site.urls),
    path("explorer/", include("explorer.urls")),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
]

urlpatterns_static = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns = urlpatterns_apps + urlpatterns_app_openapi + urlpatterns_docs + urlpatterns_django + urlpatterns_static

for version in versions:
    x = path(f"{version}/", include((versions[version], version), namespace=version))
    urlpatterns.append(x)

if os.getenv("ALLOW_UNSAFE_CYPRESS_APP") or os.environ.get("ENV") == "test":
    urlpatterns.append(path("v1/cypress/", include("breathecode.cypress.urls", namespace="cypress")))
