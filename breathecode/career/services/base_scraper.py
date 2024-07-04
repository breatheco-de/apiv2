import re

from abc import ABC, abstractmethod
from ..models import Job, Employer, PositionAlias, CareerTag, Location, LocationAlias
from breathecode.career.services.regex import _cases_salary, _cases_date


class BaseScraper(ABC):

    @abstractmethod
    def get_location_from_string(self, location: str):
        pass

    @abstractmethod
    def get_salary_from_string(self, salary: str):
        pass

    @classmethod
    def get_position_from_string(cls, keyword: str):
        alias = PositionAlias.objects.filter(name__iexact=keyword).first()

        if alias is None:
            return None

        return alias.position

    @classmethod
    def save_location(cls, keyword: str):
        if keyword != None:
            location = Location.objects.filter(name__iexact=keyword).first()
            location_alias = LocationAlias.objects.filter(name__iexact=keyword).first()

            if location is None:
                location = Location(name=keyword)
                location.save()

            if location_alias is None:
                location_alias = LocationAlias(name=keyword, location=location)
                location_alias.save()

            return location

    @classmethod
    def get_employer_from_string(cls, keyword: str):
        return Employer.objects.filter(name__iexact=keyword).first()

    @classmethod
    def save_tag(cls, keyword: str):
        tag_slug = keyword.replace(" ", "-").replace(".", "-").lower()
        tag = CareerTag.objects.filter(slug__iexact=tag_slug).first()

        if tag is None:
            tag = CareerTag(slug=tag_slug)
            tag.save()

        return tag

    @classmethod
    def job_exist(cls, title: str, employer_name: str):
        return isinstance(Job.objects.filter(title__iexact=title, employer__name=employer_name).first(), Job)

    @classmethod
    def get_pk_location(cls, location: list):
        if isinstance(location, list):
            location_pk = None

            if len(location) > 1:
                location_pk = location[0]

        return location_pk

    @classmethod
    def get_date_from_string(cls, date: str):
        for regex in _cases_date:
            findings = re.findall(regex, date)
            if findings:
                return _cases_date[regex](findings, date)

    @classmethod
    def get_salary_format_from_string(cls, salary: str):
        for regex in _cases_salary:
            findings = re.findall(regex, salary)
            if findings:
                return _cases_salary[regex](findings, salary)

    @classmethod
    def get_job_id_from_string(cls, string: str):
        if string:
            regex = r"^(\d{1,9})\/(\d{1,3})\/(\d{1,3})$"
            result = re.findall(regex, string).pop()
            deploy, num_spider, num_job = result
            return (int(deploy), int(num_spider), int(num_job))

    @classmethod
    def get_info_amount_jobs_saved(cls, data: list):
        items = 0

        num_job = data[0]["num_job"]
        if isinstance(data, list):
            for dat in data:
                if num_job < dat["num_job"]:
                    num_job = dat["num_job"]

                items += dat["jobs_saved"]

        return (items, num_job)
