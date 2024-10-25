import asyncio
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypedDict, Unpack

from adrf.requests import AsyncRequest
from asgiref.sync import sync_to_async
from capyc.core.managers import feature
from capyc.rest_framework.exceptions import PaymentException, ValidationException
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.models import User
from breathecode.payments.signals import consume_service

from ..exceptions import ProgrammingError

__all__ = ["consume", "Consumer", "ServiceContext"]

logger = logging.getLogger(__name__)


class Flags(TypedDict):
    bypass_consumption: bool


class FlagsParams(Flags, total=False):
    pass


class ServiceContext(TypedDict):
    utc_now: datetime
    consumer: bool
    service: str
    request: WSGIRequest | AsyncRequest
    consumables: QuerySet
    lifetime: Optional[timedelta]
    price: float
    is_consumption_session: bool
    flags: Flags


type Consumer = Callable[[ServiceContext, tuple, dict], tuple[ServiceContext, tuple, dict, Optional[timedelta]]]


def render_message(
    r,
    msg,
    btn_label=None,
    btn_url=None,
    btn_target="_blank",
    data=None,
    status=None,
    go_back=None,
    url_back=None,
    academy=None,
):
    if data is None:
        data = {}

    _data = {
        "MESSAGE": msg,
        "BUTTON": btn_label,
        "BUTTON_TARGET": btn_target,
        "LINK": btn_url,
        "GO_BACK": go_back,
        "URL_BACK": url_back,
    }

    if academy:
        _data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        _data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        _data["COMPANY_LOGO"] = academy.logo_url
        _data["COMPANY_NAME"] = academy.name

        if "heading" not in _data:
            _data["heading"] = academy.name

    return render(r, "message.html", {**_data, **data}, status=status)


def render_html_error(request, kwargs, service, e):
    from breathecode.events.models import Event
    from breathecode.payments.models import PlanFinancing, PlanOffer, Subscription

    token = None
    if "token" in kwargs and kwargs["token"] is not None:
        token = kwargs["token"].key

    if "service_slug" in kwargs:
        slug = kwargs["service_slug"]

    if "event_id" in kwargs:
        event_id = kwargs["event_id"]
        event = Event.objects.filter(id=event_id).first()
        if event is not None:
            slug = event.event_type.slug

    if "event" in kwargs:
        event = kwargs["event"]
        slug = event.event_type.slug

    if "mentorship_service" in kwargs:
        slug = kwargs["mentorship_service"].slug

    renovate_consumables = {}
    subscription = None
    plan_financing = None
    mentorship_service_set = None
    event_type_set = None
    plan_offer = None
    user_plan = None

    if service == "join_mentorship":
        subscription = Subscription.objects.filter(
            user=request.user, selected_mentorship_service_set__mentorship_services__slug=slug
        ).first()
        if subscription is not None:
            mentorship_service_set = subscription.selected_mentorship_service_set.slug
            user_plan = subscription.plans.first()
    elif service == "event_join":
        subscription = Subscription.objects.filter(
            user=request.user, selected_event_type_set__event_types__slug=slug
        ).first()
        if subscription is not None:
            event_type_set = subscription.selected_event_type_set.slug
            user_plan = subscription.plans.first()

    if subscription is None:
        if service == "join_mentorship":
            plan_financing = PlanFinancing.objects.filter(
                user=request.user, selected_mentorship_service_set__mentorship_services__slug=slug
            ).first()
            if plan_financing is not None:
                mentorship_service_set = plan_financing.selected_mentorship_service_set.slug
                user_plan = plan_financing.plans.first()
        elif service == "event_join":
            plan_financing = PlanFinancing.objects.filter(
                user=request.user, selected_event_type_set__event_types__slug=slug
            ).first()
            if plan_financing is not None:
                event_type_set = plan_financing.selected_event_type_set.slug
                user_plan = plan_financing.plans.first()

    if user_plan:
        plan_offer = PlanOffer.objects.filter(original_plan__slug=user_plan.slug).first()

    if plan_offer is not None:
        renovate_consumables["btn_label"] = "Get more consumables"
        renovate_consumables["btn_url"] = (
            f"https://4geeks.com/checkout?plan={plan_offer.suggested_plan.slug}&token={token}"
        )
    elif subscription is not None or plan_financing is not None:
        renovate_consumables["btn_label"] = "Get more consumables"
        if service == "join_mentorship":
            renovate_consumables["btn_url"] = (
                f"https://4geeks.com/checkout/mentorship/{mentorship_service_set}?token={token}"
            )
        elif service == "event_join":
            renovate_consumables["btn_url"] = f"https://4geeks.com/checkout/event/{event_type_set}?token={token}"
    else:
        if service == "join_mentorship" or service == "event_join":
            e = "You must get a plan in order to access this service"
            renovate_consumables["btn_label"] = "Get a plan"
            plan = os.getenv("BASE_PLAN", "basic")
            renovate_consumables["btn_url"] = f"https://4geeks.com/checkout?plan={plan}&token={token}"

    return render_message(
        request,
        str(e),
        status=402,
        go_back="Go back to Dashboard",
        url_back="https://4geeks.com/choose-program",
        **renovate_consumables,
    )


def consume(service: str, consumer: Optional[Consumer] = None, format: str = "json") -> callable:
    """Check if the current user can access to the resource through of permissions."""

    from breathecode.payments.models import Consumable, ConsumptionSession

    def decorator(function: callable) -> callable:

        def validate_and_get_request(permission: str, args: Any) -> WSGIRequest | AsyncRequest:
            if isinstance(permission, str) == False:
                raise ProgrammingError("Service must be a string")

            try:
                if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError("Missing request information, use this decorator with DRF View")

            return request

        def build_context(
            request: WSGIRequest | AsyncRequest,
            utc_now: datetime,
            flags: Optional[FlagsParams] = None,
            **opts: Unpack[ServiceContext],
        ) -> ServiceContext:

            if flags is None:
                flags = {}

            return {
                "utc_now": utc_now,
                "consumer": consumer,
                "service": service,
                "request": request,
                "consumables": Consumable.objects.none(),
                "lifetime": None,
                "price": 1,
                "is_consumption_session": False,
                "flags": {
                    "bypass_consumption": False,
                    **flags,
                },
                **opts,
            }

        def wrapper(*args, **kwargs):
            request = validate_and_get_request(service, args)

            if isinstance(request.user, AnonymousUser):
                raise PaymentException(
                    f"Anonymous user do not have enough credits to access to this service: {service}",
                    slug="anonymous-user-not-enough-consumables",
                )

            try:
                utc_now = timezone.now()
                session = ConsumptionSession.get_session(request)
                context = build_context(request, utc_now)

                if session and callable(consumer):
                    context["is_consumption_session"] = True
                    context, args, kwargs = consumer(context, args, kwargs)

                if session:
                    return function(*args, **kwargs)

                items = Consumable.list(user=request.user, service=service)
                context["consumables"] = items

                flag_context = feature.context(context=context, kwargs=kwargs)
                bypass_consumption = feature.is_enabled("payments.bypass_consumption", flag_context, False)
                context["flags"]["bypass_consumption"] = bypass_consumption

                if callable(consumer):
                    context, args, kwargs = consumer(context, args, kwargs)

                if bypass_consumption:
                    return function(*args, **kwargs)

                # exclude consumables that is being used in a session.
                if consumer and context["lifetime"]:
                    consumables = context["consumables"]
                    for item in consumables.filter(consumptionsession__status="PENDING").exclude(how_many=0):

                        sum = item.consumptionsession_set.filter(status="PENDING").aggregate(Sum("how_many"))

                        if item.how_many - sum["how_many__sum"] == 0:
                            context["consumables"] = context["consumables"].exclude(id=item.id)

                if context["price"] and context["consumables"].count() == 0:
                    raise PaymentException(
                        f"You do not have enough credits to access this service: {service}",
                        slug="with-consumer-not-enough-consumables",
                    )

                if context["price"] and context["lifetime"] and (consumable := context["consumables"].first()):
                    session = ConsumptionSession.build_session(request, consumable, context["lifetime"])

                # sync view method
                response: Response = function(*args, **kwargs)

                it_will_consume = context["price"] and response.status_code < 400
                if it_will_consume and session:
                    session.will_consume(context["price"])

                elif it_will_consume:
                    item = context["consumables"].first()
                    consume_service.send_robust(instance=item, sender=item.__class__, how_many=context["price"])

                return response

            # handle html views errors
            except PaymentException as e:
                if format == "websocket":
                    raise e

                if format == "html":
                    return render_html_error(request, kwargs, service, e)

                return Response({"detail": str(e), "status_code": 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == "websocket":
                    raise e

                status = e.status_code if hasattr(e, "status_code") else 400

                if format == "html":
                    return render_message(request, str(e), status=status)

                return Response({"detail": str(e), "status_code": status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == "html":
                    return render_message(request, "unexpected error, contact admin if you are affected", status=500)

                response = JsonResponse({"detail": str(e), "status_code": 500})
                response.status_code = 500
                return response

        @sync_to_async
        def async_get_user(request: AsyncRequest) -> User:
            return request.user

        # TODO: reduce the difference between sync and async handlers
        async def async_wrapper(*args, **kwargs):
            nonlocal consumer

            request = validate_and_get_request(service, args)

            if isinstance(request.user, AnonymousUser):
                raise PaymentException(
                    f"Anonymous user do not have enough credits to access to this service: {service}",
                    slug="anonymous-user-not-enough-consumables",
                )

            try:
                utc_now = timezone.now()
                session = await ConsumptionSession.aget_session(request)
                context = build_context(request, utc_now)

                if session and callable(consumer):
                    if asyncio.iscoroutinefunction(consumer) is False:
                        consumer = sync_to_async(consumer)

                    context["is_consumption_session"] = True
                    context, args, kwargs = await consumer(context, args, kwargs)

                if session:
                    return await function(*args, **kwargs)

                user = await async_get_user(request)

                items = await Consumable.alist(user=user, service=service)
                context["consumables"] = items

                flag_context = feature.context(context=context, kwargs=kwargs)
                bypass_consumption = feature.is_enabled("payments.bypass_consumption", flag_context, False)
                context["flags"]["bypass_consumption"] = bypass_consumption

                if callable(consumer):
                    if asyncio.iscoroutinefunction(consumer) is False:
                        consumer = sync_to_async(consumer)

                    context, args, kwargs = await consumer(context, args, kwargs)

                if bypass_consumption:
                    return await function(*args, **kwargs)

                # exclude consumables that is being used in a session.
                if consumer and context["lifetime"]:
                    consumables: QuerySet[Consumable] = context["consumables"]
                    for item in consumables.filter(consumptionsession__status="PENDING").exclude(how_many=0):

                        sum = await item.consumptionsession_set.filter(status="PENDING").aaggregate(Sum("how_many"))

                        if item.how_many - sum["how_many__sum"] == 0:
                            context["consumables"] = context["consumables"].exclude(id=item.id)

                if context["price"] and await context["consumables"].acount() == 0:
                    raise PaymentException(
                        f"You do not have enough credits to access this service: {service}",
                        slug="with-consumer-not-enough-consumables",
                    )

                if context["price"] and context["lifetime"] and (consumable := await context["consumables"].afirst()):
                    session = await ConsumptionSession.abuild_session(request, consumable, context["lifetime"])

                # sync view method
                response: Response = await function(*args, **kwargs)

                it_will_consume = context["price"] and response.status_code < 400
                if it_will_consume and session:
                    await session.awill_consume(context["price"])

                elif it_will_consume:
                    item = await context["consumables"].afirst()
                    consume_service.send_robust(instance=item, sender=item.__class__, how_many=context["price"])

                return response

            # handle html views errors
            except PaymentException as e:
                if format == "websocket":
                    raise e

                if format == "html":
                    return render_html_error(request, kwargs, service, e)

                return Response({"detail": str(e), "status_code": 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == "websocket":
                    raise e

                status = e.status_code if hasattr(e, "status_code") else 400

                if format == "html":
                    return render_message(request, str(e), status=status)

                return Response({"detail": str(e), "status_code": status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == "html":
                    return render_message(request, "unexpected error, contact admin if you are affected", status=500)

                response = JsonResponse({"detail": str(e), "status_code": 500})
                response.status_code = 500
                return response

        if asyncio.iscoroutinefunction(function):
            return async_wrapper

        return wrapper

    return decorator
