import re
from typing import Any, Optional, Type, TypedDict, Unpack, overload

from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments.models import CohortSet, EventTypeSet, MentorshipServiceSet, Service, ServiceItem

__all__ = ["consumable", "service_item", "ConsumableType", "reset_cache"]


class GenericType(TypedDict):
    id: int
    slug: str


class ServiceType(GenericType):
    type: Service.Type


class ServiceItemType(TypedDict):
    service: ServiceType
    unit_type: str
    how_many: int


class ConsumableType(TypedDict):
    service_item: ServiceItemType
    cohort_set: Optional[GenericType]
    event_type_set: Optional[GenericType]
    mentorship_service_set: Optional[GenericType]


type ID = dict[str, Any]
SERVICES: dict[ID, ServiceType] = {}
SERVICE_ITEMS: dict[ID, ServiceItemType] = {}
# VIRTUAL_SERVICE_ITEMS: list[ServiceItemType] = []
FIELDS: dict[str, tuple[str, ...]] = {
    "Service": ("id", "slug", "type"),
}

FIELDS["ServiceItem"] = ("id", "unit_type", "how_many", "service_id", *(f"service__{x}" for x in FIELDS["Service"]))

type Model = Type[Service | ServiceItem]


def get_hash(d: dict[str, Any]) -> str:
    return tuple(sorted(d.items()))


@overload
def serialize(model: Type[Service], **kwargs: Any) -> ServiceType: ...


@overload
def serialize(model: Type[ServiceItem], **kwargs: Any) -> ServiceItemType: ...


@overload
def serialize(instance: ServiceItem, **kwargs: Any) -> ServiceItemType: ...


@overload
def serialize(instance: Service, **kwargs: Any) -> ServiceType: ...


def serialize(
    model: Optional[Type[Model]] = None, instance: Optional[Model] = None, **kwargs: Any
) -> ServiceType | ServiceItemType:
    if model is None and instance is None:
        raise ValueError("Either model or instance must be provided")

    if model and instance:
        raise ValueError("Both model and instance cannot be provided")

    if model:
        key = model.__name__
    else:
        key = instance.__class__.__name__

    fields = FIELDS.get(key, tuple())

    result = {}
    if not instance:
        instance = model.objects.filter(**kwargs).only(*fields).first()

    if not instance:
        raise ValidationException(f"{key} with params {kwargs} not found")

    for field in fields:
        override = field
        if "__" in field:
            continue

        if field.endswith("_id"):
            override = field.replace("_id", "")

        result[override] = getattr(instance, override)

    if key == "Service":
        SERVICES[get_hash(kwargs)] = result
    elif key == "ServiceItem":
        SERVICE_ITEMS[get_hash(kwargs)] = result

    return result


def get_service(id: int) -> ServiceType:
    key = {"id": id}

    if get_hash(key) in SERVICES:
        return SERVICES[get_hash(key)]

    return serialize(model=Service, **key)


def get_service_item(id: int) -> ServiceItemType:
    key = {"id": id}
    if get_hash(key) in SERVICE_ITEMS:
        return SERVICE_ITEMS[get_hash(key)]

    v = serialize(model=ServiceItem, **key)
    v["service"] = serialize(instance=v["service"])
    return v


def service_item(service: ServiceType | int, **kwargs: Unpack[ServiceItemType]) -> ServiceItemType:
    if isinstance(service, int):
        service = get_service(service)

    kwargs["unit_type"] = kwargs["unit_type"].upper()

    return {"service": service, **kwargs}


class GenericType(TypedDict):
    id: int
    slug: str


# EXITS: set[str] = set()
EXISTS: dict[str, GenericType] = {}


# def serialize_generic(instance: EventTypeSet | CohortSet | MentorshipServiceSet) -> GenericType:
#     return {
#         "id": instance.id,
#         "slug": instance.slug,
#     }


def camel_to_snake(name):
    # Add an underscore before each capital letter and convert the string to lowercase
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Handle cases where there are multiple capital letters in a row
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def resource(model: Type[EventTypeSet | CohortSet | MentorshipServiceSet], **kwargs: dict[str, Any]) -> GenericType:
    name = model.__name__
    key = f"{camel_to_snake(name)}__{kwargs}"
    if key not in EXISTS:
        x = model.objects.filter(**kwargs).only("id", "slug").first()
        if not x:
            raise ValidationException(f"{name} with {kwargs} not found")

        EXISTS[key] = {"id": x.id, "slug": x.slug}

    return EXISTS[key]


def reset_cache():
    global EXISTS, SERVICES, SERVICE_ITEMS
    EXISTS = {}
    SERVICES = {}
    SERVICE_ITEMS = {}


def consumable(
    *,
    service_item: ServiceItemType | int,
    cohort_set: Optional[int] = None,
    event_type_set: Optional[int] = None,
    mentorship_service_set: Optional[int] = None,
) -> ConsumableType:

    if cohort_set:
        cohort_set = resource(CohortSet, id=cohort_set)

    if event_type_set:
        event_type_set = resource(EventTypeSet, id=event_type_set)

    if mentorship_service_set:
        mentorship_service_set = resource(MentorshipServiceSet, id=mentorship_service_set)

    if isinstance(service_item, int):
        service_item = get_service_item(service_item)

    return {
        "service_item": service_item,
        "cohort_set": cohort_set,
        "event_type_set": event_type_set,
        "mentorship_service_set": mentorship_service_set,
        "user": 1,
        "subscription_seat": None,
        "subscription_billing_team": None,
    }
