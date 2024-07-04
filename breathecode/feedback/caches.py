from breathecode.utils import Cache

from .models import Answer


class AnswerCache(Cache):
    model = Answer
