from breathecode.utils import Cache
from .models import Cohort

MODULE = 'admissions'


class CohortCache(Cache):
    model = Cohort
    depends = ['Academy', 'Syllabus']
    parents = ['CohortUser', 'Task', 'UserInvite', 'UserSpecialty', 'Survey', 'SlackChannel']
