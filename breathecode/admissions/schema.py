import graphene
from graphql.type.definition import GraphQLResolveInfo
from graphene_django import DjangoObjectType

from breathecode.admissions import models


def get_graphql_fields(info):
    """Retrieve the queried fields from the GraphQL query."""
    field_nodes = info.field_nodes[0].selection_set.selections
    return [field.name.value for field in field_nodes]


def get_model_fields(model):
    return [field.name for field in model._meta.get_fields()]


class CohortTimeSlot(DjangoObjectType):

    class Meta:
        model = models.CohortTimeSlot
        # Assuming you want to fetch all fields from the Academy model.


class Academy(DjangoObjectType):

    class Meta:
        model = models.Academy
        # Assuming you want to fetch all fields from the Academy model.


class SyllabusVersion(DjangoObjectType):

    class Meta:
        model = models.SyllabusVersion


class SyllabusSchedule(DjangoObjectType):

    class Meta:
        model = models.SyllabusSchedule


class Cohort(DjangoObjectType):

    class Meta:
        model = models.Cohort

    academy = graphene.Field(Academy)
    syllabus_version = graphene.Field(SyllabusVersion)
    schedule = graphene.Field(SyllabusSchedule)

    timeslots = graphene.List(CohortTimeSlot)

    def resolve_timeslots(self, info, page=1, limit=10):
        fields = get_model_fields(models.CohortTimeSlot)
        start = (page - 1) * limit
        end = start + limit
        return self.cohorttimeslot_set.all().defer(*fields)[start:end]


class Admissions(graphene.ObjectType):
    hello = graphene.String(default_value='Hi!')
    cohorts = graphene.List(Cohort, page=graphene.Int(), limit=graphene.Int(), plan=graphene.Boolean())

    def resolve_cohorts(self, info: GraphQLResolveInfo, plan=False, page=1, limit=10):
        fields = get_model_fields(models.Cohort)
        start = (page - 1) * limit
        end = start + limit
        return models.Cohort.objects.all().defer(*fields)[start:end]
