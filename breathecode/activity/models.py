import json
from google.cloud import ndb
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, Interval
from sqlalchemy.ext.declarative import declarative_base


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


Base = declarative_base()


class Activity(Base):
    __tablename__ = '4geeks.activity'

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False)
    kind = Column(String(25), nullable=False)
    resource = Column(String(30), nullable=True)
    resource_id = Column(String(30), nullable=True)
    meta = Column(String, default='\{\}')
    timestamp = Column(TIMESTAMP, nullable=False)
    duration = Column(String(17), nullable=True)

    @property
    def json(self):
        return json.loads(self.meta)

    @json.setter
    def json(self, value):
        self.meta = json.dumps(value)
