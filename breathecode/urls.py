"""breathecode URL Configuration

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
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from rest_framework import routers
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="BreatheCode API",
        default_version='v1',
        description="Technology for Learning",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny, ),
)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json'),
    url(r'^swagger/$',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'),
    url(r'^redoc/$',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'),
    path('admin/', admin.site.urls),
    path('v1/auth/', include('breathecode.authenticate.urls',
                             namespace='auth')),
    path('v1/admissions/',
         include('breathecode.admissions.urls', namespace='admissions')),
    path('v1/assignment/',
         include('breathecode.assignments.urls', namespace='assignments')),
    path('v1/freelance/',
         include('breathecode.freelance.urls', namespace='freelance')),
    path('v1/events/', include('breathecode.events.urls', namespace='events')),
    path('v1/registry/',
         include('breathecode.registry.urls', namespace='registry')),
    path('v1/activity/',
         include('breathecode.activity.urls', namespace='activity')),
    path('v1/feedback/',
         include('breathecode.feedback.urls', namespace='feedback')),
    path('v1/messaging/', include('breathecode.notify.urls',
                                  namespace='notify')),
    path('v1/assessment/',
         include('breathecode.assessment.urls', namespace='assessment')),
    path('v1/certificate/',
         include('breathecode.certificate.urls', namespace='certificate')),
    path('v1/media/', include('breathecode.media.urls', namespace='media')),
    path('v1/marketing/',
         include('breathecode.marketing.urls', namespace='marketing')),
    path('s/',
         include('breathecode.marketing.urls_shortner', namespace='shortner')),
]
