from breathecode.utils import Cache


class CohortCache(Cache):
    model = 'Cohort'
    depends = ['Academy', 'Syllabus']
    parents = [
        'CohortUser', 'Task', 'UserInvite', 'UserSpecialty', 'Survey',
        'SlackChannel'
    ]
