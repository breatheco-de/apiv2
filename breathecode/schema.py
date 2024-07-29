# flake8: noqa: N802

import graphene
from breathecode.admissions.schema import Admissions


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hi!")
    Admissions = graphene.Field(Admissions)

    def resolve_Admissions(self, info):
        return Admissions()


schema = graphene.Schema(query=Query)
