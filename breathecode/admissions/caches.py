from breathecode.utils import Cache
from .models import Cohort, CohortUser
from breathecode.authenticate.models import ProfileAcademy

MODULE = 'admissions'


class CohortCache(Cache):
    model = Cohort
    depends = ['Academy', 'SyllabusVersion', 'SyllabusSchedule']
    parents = [
        'CohortUser', 'Task', 'UserInvite', 'UserSpecialty', 'Survey', 'SlackChannel', 'CohortTimeSlot',
        'FinalProject', 'GitpodUser', 'Answer', 'Review'
    ]


class TeacherCache(Cache):
    model = ProfileAcademy
    depends = ['Academy', 'User', 'Cohort', 'Role']
    parents = []


class CohortUserCache(Cache):
    model = CohortUser
    depends = ['User', 'Cohort']
    parents = []
