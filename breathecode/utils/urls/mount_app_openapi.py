from django.urls.conf import path
from rest_framework.schemas import get_schema_view
from rest_framework import permissions

__all__ = ["mount_app_openapi"]


def mount_app_openapi(url: str, urlconf, namespace):
    if not url.startswith("/"):
        url = "/" + url

    return path(
        f"openapi/{namespace}.yml",
        get_schema_view(
            url=url,
            public=True,
            permission_classes=(permissions.AllowAny,),
            urlconf=urlconf,
        ),
        name=f"{namespace}-openapi-schema",
    )
