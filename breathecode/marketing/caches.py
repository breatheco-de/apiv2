from breathecode.utils import Cache
from .models import Course


class CourseCache(Cache):
    model = Course
    depends = ['Academy', 'Syllabus']
    parents = ['CourseTranslation']
