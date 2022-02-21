from breathecode.jobs.services import BaseScrapper
from ..models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject

__all__ = ['LinkedintScrapper']


class LinkedintScrapper(BaseScrapper):
    def get_location_from_string(text: str):
        location, remote = BaseScrapper.get_regex_from_string(text)

        if isinstance(location, list):
            locations = [BaseScrapper.save_location(x) for x in location]

        return (locations, remote)

    def get_position_from_string(cls, text: str):
        pass

    def get_dates_from_string(cls, text: str):
        pass

    def get_salary_from_string(cls, text: str):
        pass
