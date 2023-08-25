import json
import os
from google.cloud import ndb
from sqlalchemy import Column, Integer, String, TIMESTAMP, JSON

from breathecode.utils.sqlalchemy import BigQueryBase, test_support


def is_test_env():
    return os.getenv('ENV') == 'test' or True


class StudentActivity(ndb.Model):
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


class ActivityMeta(BigQueryBase):
    __tablename__ = '4geeks.activity_nested'
    # if is_test_env():
    #     __tablename__ = '4geeks_activity_nested'

    # else:
    #     __tablename__ = '4geeks.activity_nested'

    #
    email = Column(String(36), primary_key=True)
    related = Column(Integer, nullable=False)
    related_pk = Column(String(25), nullable=False)
    # related
    resource = Column(String(30), nullable=True)
    resource_id = Column(String(30), nullable=True)
    meta = Column(String, default='\{\}')
    meta = Column(JSON, default='\{\}')
    timestamp = Column(TIMESTAMP, nullable=False)


class Activity(BigQueryBase):
    __tablename__ = '4geeks.activity'
    # if is_test_env():
    #     __tablename__ = '4geeks_activity'

    # else:
    #     __tablename__ = '4geeks.activity'

    #
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False)
    kind = Column(String(25), nullable=False)
    # related
    resource = Column(String(30), nullable=True)
    resource_id = Column(String(30), nullable=True)
    meta = Column(String, default='\{\}')
    meta = Column(JSON, default='\{\}')
    timestamp = Column(TIMESTAMP, nullable=False)
    # duration = Column(String(17), nullable=True)

    @property
    def json(self):
        return json.loads(self.meta)

    @json.setter
    def json(self, value):
        self.meta = json.dumps(value)


test_support(__name__)
