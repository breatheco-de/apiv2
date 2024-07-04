from breathecode.utils import Cache

from .models import MentorProfile


class MentorProfileCache(Cache):
    model = MentorProfile
