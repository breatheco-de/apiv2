from django.db import models
from django.contrib.auth.models import User

# models here
from datetime import datetime
from google.cloud import ndb


class Activity(ndb.Model):
    id = ndb.ModelKey()
    cohort = ndb.StringProperty()
    created_at = ndb.DateTimeProperty()
    data = ndb.JsonProperty()
    day = ndb.IntegerProperty()
    email = ndb.StringProperty()
    slug = ndb.StringProperty()
    user_agent = ndb.StringProperty()
    user_id = ndb.IntegerProperty()
    academy_id = ndb.IntegerProperty()

    @classmethod
    def _get_kind(cls):
        return 'student_activity'
