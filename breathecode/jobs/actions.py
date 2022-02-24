import requests
import os
import logging
import re
from .models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject
from breathecode.utils import ValidationException
from datetime import datetime, timedelta
from breathecode.jobs.services import ScraperFactory

logger = logging.getLogger(__name__)


def run_spider(spider):
    platform = spider.zyte_project.platform.name
    class_scrapper = ScraperFactory(platform)

    if spider is None:
        logger.debug(f'First you must specify a spider (run_spider)')
        raise ValidationException('First you must specify a spider', slug='missing-spider')

    position = class_scrapper.get_position_from_string(spider.job)
    if position is None:
        positionAlias = PositionAlias()
        positionAlias.name = spider.job
        positionAlias.position = spider.position
        positionAlias.save()

    data = {
        'project': spider.zyte_project.zyte_api_deploy,
        'spider': spider.zyte_project.platform.name,
        'job': spider.job,
    }

    data['loc'] = spider.loc
    response = requests.post('https://app.scrapinghub.com/api/run.json',
                             data=data,
                             auth=(spider.zyte_project.zyte_api_key, ''))

    result = response.json()

    return (response.status_code == 200 and 'status' in result and result['status'] == 'ok', result)


def fetch_to_api(spider):
    if spider is None:
        logger.debug(f'First you must specify a spider (fetch_to_api)')
        raise ValidationException('First you must specify a spider', slug='without-spider')

    params = (
        ('project', spider.zyte_project.zyte_api_deploy),
        ('spider', spider.zyte_project.platform.name),
        ('state', 'finished'),
    )

    res = requests.get('https://app.scrapinghub.com/api/jobs/list.json',
                       params=params,
                       auth=(spider.zyte_project.zyte_api_key, '')).json()

    return res


def fetch_data_to_json(spider, api_fetch):
    if spider is None:
        logger.error(f'First you must specify a spider (fetch_data_to_json)')
        raise ValidationException('First you must specify a spider', slug='without-spider')

    if api_fetch is None:
        logger.error(f'I did not receive results from the API (fetch_data_to_json)')
        raise ValidationException('Is did not receive results from the API', slug='no-return-json-data')

    platform = spider.zyte_project.platform.name
    class_scrapper = ScraperFactory(platform)
    data_project = []

    for res_api_jobs in api_fetch['jobs']:
        deploy, num_spider, num_job = class_scrapper.get_job_id_from_string(res_api_jobs['id'])
        if int(num_spider) == int(spider.zyte_spider_number) and int(num_job) >= int(spider.zyte_job_number):
            response = requests.get(
                f'https://storage.scrapinghub.com/items/{res_api_jobs["id"]}?apikey={spider.zyte_project.zyte_api_key}&format=json'
            )

            if response.status_code != 200:
                logger.error(
                    f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spider} (fetch_data_to_json)'
                )
                raise ValidationException(
                    f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spider}',
                    slug='bad-resmponse-fetch')

            new_jobs = save_data(spider, response.json())
            data_project.append({
                'status': 'ok',
                'platform_name': spider.zyte_project.platform.name,
                'num_spider': int(num_spider),
                'num_job': int(num_job),
                'jobs_saved': new_jobs
            })

    return data_project


def save_data(spider, jobs):
    platform = spider.zyte_project.platform.name
    class_scrapper = ScraperFactory(platform)
    new_jobs = 0

    for j in jobs:
        locations, remote = class_scrapper.get_location_from_string(j['Location'])
        location_pk = class_scrapper.get_pk_location(locations)

        employer = class_scrapper.get_employer_from_string(j['Company_name'])
        #TODO ASK TO ALEJANDRO EMPOLYER WITH MANY TO COMPANY
        if employer is None:
            employer = Employer(name=j['Company_name'], location=location_pk)
            employer.save()

        position = class_scrapper.get_position_from_string(j['Searched_job'])
        if position is None:
            position = Position(name=j['Searched_job'])
            position.save()

            positionAlias = PositionAlias(name=j['Searched_job'], position=position)
            positionAlias.save()

        (min_salary, max_salary, salary_str,
         tags) = class_scrapper.get_salary_from_string(j['Salary'], j['Tags'])
        if tags is not None:
            for tag in tags:
                t = tag.replace(' ', '-').lower()
                tagsave = class_scrapper.get_tag_from_string(t)
                if tagsave is None:
                    Tag.objects.create(slug=t)

        validate = class_scrapper.job_exist(j['Job_title'], j['Company_name'])
        if validate is False:
            job = Job(
                title=j['Job_title'],
                platform=spider.zyte_project.platform,
                published_date_raw=j['Post_date'],
                apply_url=j['Apply_to'],
                salary=salary_str,
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

            if tags is not None:
                for tag in tags:
                    _tag = class_scrapper.get_tag_from_string(tag)
                    if _tag is not None:
                        job.tags.add(_tag)

            new_jobs = new_jobs + 1

    return new_jobs


def fetch_sync_all_data(spider):
    if spider is None:
        logger.debug(f'First you must specify a spider (fetch_sync_all_data)')
        raise ValidationException('First you must specify a spider', slug='without-spider')

    res = fetch_to_api(spider)

    data_jobs = fetch_data_to_json(spider, res)
    platform = spider.zyte_project.platform.name
    class_scrapper = ScraperFactory(platform)

    jobs_info_saverd = class_scrapper.count_jobs_saved(data_jobs)
    if isinstance(jobs_info_saverd, tuple):
        job_saved, job_namber = jobs_info_saverd
        spider.zyte_job_number = job_namber
        spider.zyte_last_fetch_date = datetime.now()
        spider.status = 'SYNCHED'
        spider.sync_status = 'SYNCHED'
        spider.sync_desc = f"The spider's career ended successfully. Added {job_saved} new jobs to {spider.name} at " + str(
            datetime.now())
        spider.save()

    return res


def parse_date(job):

    if job is None:
        logger.debug(f'First you must specify a job (parse_date)')
        raise ValidationException('First you must specify a job', slug='data-job-none')

    platform = job.platform.name
    class_scrapper = ScraperFactory(platform)
    job.published_date_processed = class_scrapper.get_date_from_string(job.published_date_raw)
    job.save()

    return job
