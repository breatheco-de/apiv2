import re
from breathecode.career.services import BaseScraper
from breathecode.career.services.regex import _cases_location


class GetonboardScraper(BaseScraper):

    @classmethod
    def get_location_from_string(cls, text: str):
        if text is None:
            text = "Remote"

        for regex in _cases_location:
            findings = re.findall(regex, text)
            if findings:
                locations = _cases_location[regex](findings, text)
                remote = False

                if "Remote" in locations:
                    remote = True
                    locations.remove("Remote")

                if isinstance(locations, list):
                    locations = [cls.save_location(x) for x in locations]

                return (locations, remote)

    @classmethod
    def get_salary_from_string(cls, salary):
        min_salary = 0
        max_salary = 0
        salary_str = "Not supplied"

        if salary is not None and salary != "Not supplied" and salary != "Remote":
            salary = cls.get_salary_format_from_string(salary)
            if salary:
                min_salary = float(salary[0]) * 12
                max_salary = float(salary[1]) * 12
                salary_str = f"${min_salary} - ${max_salary} a year."

        return (min_salary, max_salary, salary_str)

    @classmethod
    def get_tag_from_string(cls, tags: list):
        if not tags:
            tags = ["web-developer"]

        if isinstance(tags, list):
            tags = [cls.save_tag(x) for x in tags]

        return tags
