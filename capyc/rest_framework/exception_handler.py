from django import forms
from django.core.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from capyc.rest_framework.exceptions import PaymentException, ValidationException

__all__ = ["exception_handler"]


def get_item_attrs(item):
    data = {
        "pk": item.pk,
    }

    if hasattr(item, "slug"):
        data["slug"] = item.slug

    if hasattr(item, "name"):
        data["name"] = item.name

    return data


def exception_handler(exc, context):
    """Exception handler for Django REST Framework."""

    if isinstance(exc, (forms.ValidationError, ValidationError)):

        for k in exc.error_dict:
            for x in exc.error_dict[k]:
                err = ""
                if k != "__all__":
                    err += f"{k}: "

                err += f"{x.message}, "

            if err.endswith(", "):
                err = err[:-2] + ". "

        if err.endswith(". "):
            err = err[:-1]

        exc = ValidationException(err)

    context["request"]._request.POST = context["request"].data
    response = drf_exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        is_our_exception = isinstance(exc, ValidationException) or isinstance(exc, PaymentException)
        if is_our_exception and isinstance(exc.detail, list):

            items = []

            for x in response.data:
                data = {
                    "detail": str(x),
                    "status_code": x.status_code,
                }

                if x.silent:
                    data["silent"] = True
                    data["silent_code"] = x.slug

                if x.data:
                    data["data"] = x.data

                if x.queryset:
                    data["items"] = [get_item_attrs(v) for v in x.queryset]
                items.append(data)

            if len(items) == 1:
                items = items[0]

            response.data = items

        elif is_our_exception:
            response.data["status_code"] = response.status_code

            if exc.silent:
                response.data["silent"] = True
                response.data["silent_code"] = exc.slug

            if exc.data is not None:
                response.data["data"] = exc.data

            if exc.queryset:
                response.data["items"] = [get_item_attrs(v) for v in exc.queryset]

        elif isinstance(exc, ValidationError):
            response.data["status_code"] = 400

        elif isinstance(response.data, list):
            if response.data[0].code != "invalid":
                response.data = {"status_code": response.data[0].code, "details": str(response.data[0])}
            else:
                response.data = {"status_code": 500, "details": str(response.data[0])}

        else:
            response.data["status_code"] = response.status_code

    return response
