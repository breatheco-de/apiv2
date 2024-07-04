import logging

import requests
from django.utils import timezone

from breathecode.career.services import scraper_factory
from capyc.rest_framework.exceptions import ValidationException

from .models import Employer, Job, Position, PositionAlias, ZyteProject

logger = logging.getLogger(__name__)


def run_spider(spider):

    if spider is None:
        logger.error("First you must specify a spider (run_spider)")
        raise ValidationException("First you must specify a spider", slug="missing-spider")

    platform = spider.zyte_project.platform.name
    class_scrapper = scraper_factory(platform)

    position = class_scrapper.get_position_from_string(spider.job_search)
    if position is None:
        position_alias = PositionAlias()
        position_alias.name = spider.job_search
        position_alias.position = spider.position
        position_alias.save()

    data = {
        "project": spider.zyte_project.zyte_api_deploy,
        "spider": spider.zyte_project.platform.name,
        "job": spider.job_search,
    }

    data["loc"] = spider.loc_search
    response = requests.post(
        "https://app.scrapinghub.com/api/run.json", data=data, auth=(spider.zyte_project.zyte_api_key, ""), timeout=2
    )
    result = response.json()

    if result["status"] == "error":
        spider.spider_last_run_status = "ERROR"
        spider.spider_last_run_desc = (
            f"The spider career ended error. ({result['message']} at " + str(timezone.now()) + ")"
        )
        spider.save()
        logger.error(f'The spider ended error. Type error {result["message"]}')
    else:
        spider.spider_last_run_status = "SYNCHED"
        spider.spider_last_run_desc = f"The execution of the spider was successful to {spider.name} at " + str(
            timezone.now()
        )
        spider.save()

    return (response.status_code == 200 and "status" in result and result["status"] == "ok", result)


def fetch_to_api(spider):
    if spider is None:
        logger.debug("First you must specify a spider (fetch_to_api)")
        raise ValidationException("First you must specify a spider", slug="without-spider")

    params = (
        ("project", spider.zyte_project.zyte_api_deploy),
        ("spider", spider.zyte_project.platform.name),
        ("state", "finished"),
    )

    res = requests.get(
        "https://app.scrapinghub.com/api/jobs/list.json",
        params=params,
        auth=(spider.zyte_project.zyte_api_key, ""),
        timeout=2,
    ).json()
    return res


def get_scraped_data_of_platform(spider, api_fetch):
    if spider is None:
        logger.error("First you must specify a spider (get_scraped_data_of_platform)")
        raise ValidationException("First you must specify a spider", slug="without-spider")

    if api_fetch is None:
        logger.error("I did not receive results from the API (get_scraped_data_of_platform)")
        raise ValidationException("Is did not receive results from the API", slug="no-return-json-data")

    platform = spider.zyte_project.platform.name
    class_scrapper = scraper_factory(platform)
    data_project = []

    for res_api_jobs in api_fetch["jobs"]:
        deploy, num_spider, num_job = class_scrapper.get_job_id_from_string(res_api_jobs["id"])

        if num_spider == spider.zyte_spider_number and num_job >= spider.zyte_job_number:
            response = requests.get(
                f'https://storage.scrapinghub.com/items/{res_api_jobs["id"]}?apikey={spider.zyte_project.zyte_api_key}&format=json',
                timeout=2,
            )

            if response.status_code != 200:
                spider.sync_status = "ERROR"
                spider.sync_desc = (
                    f"There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spider} (get_scraped_data_of_platform)"
                    + str(timezone.now())
                )
                spider.save()

                logger.error(
                    f"There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spider} (get_scraped_data_of_platform)"
                )
                raise ValidationException(
                    f"There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spider}",
                    slug="bad-response-fetch",
                )

            new_jobs = save_data(spider, response.json())
            data_project.append(
                {
                    "status": "ok",
                    "platform_name": spider.zyte_project.platform.name,
                    "num_spider": int(num_spider),
                    "num_job": int(num_job),
                    "jobs_saved": new_jobs,
                }
            )

    return data_project


def save_data(spider, jobs):
    platform = spider.zyte_project.platform.name
    class_scrapper = scraper_factory(platform)
    new_jobs = 0

    for j in jobs:
        locations, remote = class_scrapper.get_location_from_string(j["Location"])
        location_pk = class_scrapper.get_pk_location(locations)

        employer = class_scrapper.get_employer_from_string(j["Company_name"])
        if employer is None:
            employer = Employer(name=j["Company_name"], location=location_pk)
            employer.save()

        position = class_scrapper.get_position_from_string(j["Searched_job"])
        if position is None:
            position = Position(name=j["Searched_job"])
            position.save()

            position_alias = PositionAlias(name=j["Searched_job"], position=position)
            position_alias.save()

        (min_salary, max_salary, salary_str) = class_scrapper.get_salary_from_string(j["Salary"])

        save_tags = class_scrapper.get_tag_from_string(j["Tags"])

        validate = class_scrapper.job_exist(j["Job_title"], j["Company_name"])
        if validate is False:
            job = Job(
                title=j["Job_title"],
                spider=spider,
                published_date_raw=j["Post_date"],
                apply_url=j["Apply_to"],
                salary=salary_str,
                job_description=j["Job_description"],
                min_salary=min_salary,
                max_salary=max_salary,
                remote=remote,
                employer=employer,
                position=position,
            )
            job.save()

            if locations is not None:
                for location in locations:
                    job.locations.add(location)

            if save_tags is not None:
                for tag in save_tags:
                    job.career_tags.add(tag)

            new_jobs = new_jobs + 1

    return new_jobs


def fetch_sync_all_data(spider):
    if spider is None:
        logger.debug("First you must specify a spider (fetch_sync_all_data)")
        raise ValidationException("First you must specify a spider", slug="without-spider")

    res = fetch_to_api(spider)
    data_jobs = get_scraped_data_of_platform(spider, res)

    platform = spider.zyte_project.platform.name
    class_scrapper = scraper_factory(platform)

    jobs_info_saved = class_scrapper.get_info_amount_jobs_saved(data_jobs)
    if isinstance(jobs_info_saved, tuple):
        job_saved, job_number = jobs_info_saved
        spider.zyte_job_number = job_number
        spider.zyte_last_fetch_date = timezone.now()
        spider.sync_status = "SYNCHED"
        spider.sync_desc = (
            f"The spider's career ended successfully. Added {job_saved} new jobs to {spider.name} at "
            + str(timezone.now())
        )
        spider.save()

        ZyteProject.objects.filter(id=spider.zyte_project.id).update(zyte_api_last_job_number=job_number)

    return res


def get_was_published_date_from_string(job):

    if job is None:
        logger.error("First you must specify a job (get_was_published_date_from_string)")
        raise ValidationException("First you must specify a job", slug="data-job-none")

    platform = job.spider.zyte_project.platform.name
    class_scrapper = scraper_factory(platform)
    job.published_date_processed = class_scrapper.get_date_from_string(job.published_date_raw)
    job.save()

    return job
