import logging
import re
import graphene
from graphql import GraphQLError
from graphql.type.definition import GraphQLResolveInfo
from graphene_django import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from breathecode.admissions import models
from breathecode.admissions.actions import haversine
from django.db.models import FloatField, Q, Value
from django.utils import timezone

logger = logging.getLogger(__name__)


def field_is_requested(info, field_name):
    """Check if a field is being requested in the current query."""
    return any(selection.name.value == field_name for selection in info.field_nodes[0].selection_set.selections)


def fields_requested(info):
    """Check if a field is being requested in the current query."""
    return [selection.name.value for selection in info.field_nodes[0].selection_set.selections]


def to_snake_case(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def optimize_queryset(queryset, to_one=None, to_many=None, custom=None, fields=None, info=None):

    if to_one is None:
        to_one = []

    if to_many is None:
        to_many = []

    if custom is None:
        custom = []

    selected_related = []
    prefetch_related = []
    only = []

    if not fields:
        fields = fields_requested(info)

    for field in fields:
        field = to_snake_case(field)

        if field in to_many:
            prefetch_related.append(field)

        elif field in to_one:
            selected_related.append(field)

        # it does not works
        # elif field not in custom and field not in selected_related and field not in prefetch_related:
        #     only.append(field)

    queryset = queryset.select_related(*selected_related).prefetch_related(*prefetch_related).only(*only)
    return queryset


class CohortTimeSlot(DjangoObjectType):

    class Meta:
        model = models.CohortTimeSlot
        fields = "__all__"


class City(DjangoObjectType):

    class Meta:
        model = models.City
        fields = "__all__"


class Country(DjangoObjectType):

    class Meta:
        model = models.Country
        fields = "__all__"

    city = graphene.Field(City)


class Academy(DjangoObjectType):

    class Meta:
        model = models.Academy
        fields = "__all__"

    country = graphene.Field(Country)
    city = graphene.Field(City)


class Syllabus(DjangoObjectType):

    class Meta:
        model = models.Syllabus
        fields = "__all__"


class SyllabusVersion(DjangoObjectType):

    class Meta:
        model = models.SyllabusVersion
        fields = "__all__"

    syllabus = graphene.Field(Syllabus)


class SyllabusSchedule(DjangoObjectType):

    class Meta:
        model = models.SyllabusSchedule
        fields = "__all__"

    syllabus = graphene.Field(Syllabus)


class Cohort(DjangoObjectType):

    class Meta:
        model = models.Cohort
        fields = "__all__"

    academy = graphene.Field(Academy)
    syllabus_version = graphene.Field(SyllabusVersion)
    schedule = graphene.Field(SyllabusSchedule)
    distance = graphene.Float()

    timeslots = graphene.List(CohortTimeSlot)

    def resolve_timeslots(self, info, first=10):
        return gql_optimizer.query(self.cohorttimeslot_set.all()[0:first], info)

    def resolve_distance(self, info):
        if not hasattr(self, "latitude") or not hasattr(self, "longitude"):
            return None

        if not self.latitude or not self.longitude or not self.academy.latitude or not self.academy.longitude:
            return None

        return haversine(self.longitude, self.latitude, self.academy.longitude, self.academy.latitude)


class Admissions(graphene.ObjectType):
    hello = graphene.String(default_value="Hi!")
    cohorts = graphene.List(
        Cohort, page=graphene.Int(), limit=graphene.Int(), plan=graphene.String(), coordinates=graphene.String()
    )

    def resolve_cohorts(self, info: GraphQLResolveInfo, page=1, limit=10, **kwargs):
        items = models.Cohort.objects.all()
        start = (page - 1) * limit
        end = start + limit

        fields = fields_requested(info)

        items = optimize_queryset(
            items, to_one=["academy", "schedule", "syllabusVersion"], to_many=[], custom=["distance"], fields=fields
        )

        has_distance = "distance" in fields

        if has_distance:
            items = items.annotate(
                longitude=Value(None, output_field=FloatField()), latitude=Value(None, output_field=FloatField())
            )

        upcoming = kwargs.get("upcoming", None)
        if upcoming == "true":
            now = timezone.now()
            items = items.filter(Q(kickoff_date__gte=now) | Q(never_ends=True))

        never_ends = kwargs.get("never_ends", None)
        if never_ends == "false":
            items = items.filter(never_ends=False)

        academy = kwargs.get("academy", None)
        if academy is not None:
            items = items.filter(academy__slug__in=academy.split(","))

        location = kwargs.get("location", None)
        if location is not None:
            items = items.filter(academy__slug__in=location.split(","))

        ids = kwargs.get("id", None)
        if ids is not None:
            items = items.filter(id__in=ids.split(","))

        slugs = kwargs.get("slug", None)
        if slugs is not None:
            items = items.filter(slug__in=slugs.split(","))

        stage = kwargs.get("stage")
        if stage:
            items = items.filter(stage__in=stage.upper().split(","))
        else:
            items = items.exclude(stage="DELETED")

        if has_distance and (coordinates := kwargs.get("coordinates", "")):
            try:
                latitude, longitude = coordinates.split(",")
                latitude = float(latitude)
                longitude = float(longitude)
            except Exception:
                raise GraphQLError("Bad coordinates, the format is latitude,longitude", slug="bad-coordinates")

            if latitude > 90 or latitude < -90:
                raise GraphQLError("Bad latitude", slug="bad-latitude")

            if longitude > 180 or longitude < -180:
                raise GraphQLError("Bad longitude", slug="bad-longitude")

            items = items.annotate(longitude=Value(longitude, FloatField()), latitude=Value(latitude, FloatField()))

        saas = kwargs.get("saas", "").lower()
        if saas == "true":
            items = items.filter(academy__available_as_saas=True)

        elif saas == "false":
            items = items.filter(academy__available_as_saas=False)

        syllabus_slug = kwargs.get("syllabus_slug", "")
        if syllabus_slug:
            items = items.filter(syllabus_version__syllabus__slug=syllabus_slug)

        plan = kwargs.get("plan", "")
        if plan == "true":
            items = items.filter(academy__main_currency__isnull=False, cohortset__isnull=False).distinct()

        elif plan == "false":
            items = items.filter().exclude(cohortset__isnull=True).distinct()

        elif plan:
            kwargs = {}

            if isinstance(plan, int) or plan.isnumeric():
                kwargs["cohortset__plan__id"] = plan
            else:
                kwargs["cohortset__plan__slug"] = plan

            items = items.filter(**kwargs).distinct()

        return items[start:end]
