from breathecode.utils import Cache
from .models import Cohort, CohortUser

MODULE = 'admissions'


class CohortCache(Cache):
    model = Cohort
    depends = ['Academy', 'SyllabusVersion', 'SyllabusSchedule']
    parents = [
        'CohortUser', 'Task', 'UserInvite', 'UserSpecialty', 'Survey', 'SlackChannel', 'CohortTimeSlot',
        'FinalProject', 'GitpodUser', 'Answer', 'Review'
    ]


class CohortUserCache(Cache):
    model = CohortUser
    depends = ['User', 'Cohort']
    parents = []
