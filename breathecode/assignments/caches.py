from breathecode.utils import Cache
from .models import Task


class TaskCache(Cache):
    model = Task
    depends = ['User', 'Cohort']
    parents = []
