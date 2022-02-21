import re
from abc import ABC, abstractmethod
from ..models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject
from breathecode.utils import ValidationException
from breathecode.jobs.services.regex import get_regex_location_from_string, get_regex_date_from_string, get_salary_format_from_regex

__all__ = ['BaseScrapper']


class BaseScrapper(ABC):
    @abstractmethod
    def get_location_from_string(cls, location: str):
        ...

    @abstractmethod
    def get_date_from_string(cls, date: str):
        ...

    @abstractmethod
    def get_salary_from_string(cls, salary: str):
        ...

    @classmethod
    def get_position_from_string(cls, keyword: str):
        alias = PositionAlias.objects.filter(name__iexact=keyword).first()

        if alias is None:
            return None

        return alias.position

    @classmethod
    def get_location_alias_from_string(cls, keyword: str):
        locations = LocationAlias.objects.filter(name__iexact=keyword).first()

        if locations is None:
            return None

        return locations

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
    def get_tag_from_string(cls, tag: str):
        return Tag.objects.filter(slug__iexact=keyword).first()

    @classmethod
    def job_exist(cls, title: str, employer_name: str):
        return bool(Job.objects.filter(title__iexact=title, employer__name=employer_name).count())

    @classmethod
    def get_regex_from_string(cls, string):
        #TODO CHANGE NOMBRE (GET LOCATION FROM STRING)
        locations = get_regex_location_from_string(string)
        remote = False

        if 'Remote' in locations:
            remote = True
            locations.remove('Remote')

        return (locations, remote)

    @classmethod
    def remove_null(cls, string):
        #TODO CHANVE NAME AND METHOD PRIVATE
        if string is None:
            string = 'Remote'
        if 'Remote (Remote from Latin America' in string:
            string = 'Remote (Latin America)'
        if 'Remote (remote from latin america' in string:
            string = 'Remote (Latin America)'
        if 'Santiago de chile' in string:
            string = 'Santiago (chile)'
        return string

    @classmethod
    def get_pk_location(cls, location: list):
        if isinstance(location, list):
            if len(location) > 1:
                location_pk = location[0]
            else:
                location_pk = None
        return location_pk

    @classmethod
    def get_regex_date_from_string(cls, date: str):
        #TODO CHANGE FUNCTION NAME
        return get_regex_date_from_string(date)

    @classmethod
    def get_salary_format_from_string(cls, salary: str):
        return get_salary_format_from_regex(salary)

    @classmethod
    def get_job_id_from_string(cls, string: str):
        regex = r'^(\d{1,9})\/(\d{1,3})\/(\d{1,3})$'
        return re.findall(regex, string).pop()
