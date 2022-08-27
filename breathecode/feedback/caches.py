from breathecode.utils import Cache
from .models import Answer


class AnswerCache(Cache):
    model = Answer
    depends = ['Event', 'MentorshipSession', 'User', 'Cohort', 'Academy', 'Survey']
    parents = []
