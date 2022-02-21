from breathecode.jobs.services import BaseScrapper

__all__ = ['GetonboardScrapper']


class GetonboardScrapper(BaseScrapper):
    @classmethod
    def get_location_from_string(cls, text: str):
        location, remote = cls.get_regex_from_string(text)

        if isinstance(location, list):
            locations = [cls.save_location(x) for x in location]

        return (locations, remote)

    @classmethod
    def get_date_from_string(cls, text: str):
        return cls.get_regex_date_from_string(text)

    @classmethod
    def get_salary_from_string(cls, salary, tags):
        min_salary = 0
        max_salary = 0
        salary_str = 'Not supplied'

        tags = tags
        if salary is not None and salary != 'Not supplied' and salary != 'Remote':
            salary = cls.get_salary_format_from_string(salary)
            if salary:
                min_salary = float(salary[0]) * 12
                max_salary = float(salary[1]) * 12
                salary_str = f'${min_salary} - ${max_salary} a year.'

        return (min_salary, max_salary, salary_str, tags)
