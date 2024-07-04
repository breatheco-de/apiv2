from django.contrib.auth.models import User

from breathecode.authenticate.models import ProfileAcademy
from breathecode.utils import Cache

from .models import Cohort, CohortUser, SyllabusVersion

MODULE = "admissions"


class CohortCache(Cache):
    model = Cohort


class TeacherCache(Cache):
    model = ProfileAcademy


class CohortUserCache(Cache):
    model = CohortUser


class UserCache(Cache):
    model = User


class SyllabusVersionCache(Cache):
    model = SyllabusVersion
