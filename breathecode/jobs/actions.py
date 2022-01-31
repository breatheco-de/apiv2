import requests, os, logging
from .models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject

import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def run_spider(spider):
    if spider is None:
        raise Exception('First you must specify a spider')

    position = get_position_from_string(spider.job)

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
        raise Exception('First you must specify a spider')

    params = (
        ('project', spider.zyte_project.zyte_api_deploy),
        ('spider', spider.zyte_project.platform.name),
        ('state', 'finished'),
    )

    count = [('count', spider.zyte_fetch_count)]

    if spider.zyte_fetch_count > 0:
        list_to_tuple(params, count)

    res = requests.get('https://app.scrapinghub.com/api/jobs/list.json',
                       params=params,
                       auth=(spider.zyte_project.zyte_api_key, '')).json()

    return res


def fetch_data_to_json(*args):
    spider, api_fetch = args

    if spider is None:
        raise Exception('First you must specify a spider')

    if api_fetch is None:
        raise Exception('First you must specify result of the api fetch')

    data_project = []
    for res_api_jobs in api_fetch['jobs']:
        print(f"{res_api_jobs['id']}")
        num_spid = get_job_id_from_string(res_api_jobs['id'])

        if int(num_spid[1]) == int(
                spider.zyte_spider_number) and int(num_spid[2]) >= int(spider.zyte_job_number):
            response = requests.get(
                f'https://storage.scrapinghub.com/items/{res_api_jobs["id"]}?apikey={spider.zyte_project.zyte_api_key}&format=json'
            )

            if response.status_code != 200:
                raise Exception(
                    f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {num_spid[1]}'
                )
            elif response.status_code == 404:
                continue
            print(
                f'https://storage.scrapinghub.com/items/{res_api_jobs["id"]}?apikey={spider.zyte_project.zyte_api_key}&format=json'
            )

            data_project.append({
                'status': 'ok',
                'platform_name': spider.zyte_project.platform.name,
                'num_spider': num_spid[1],
                'num_job': num_spid[2],
                'jobs': response.json()
            })

    return data_project


def save_data(spider, jobs):
    platform = spider.zyte_project.platform.name
    new_jobs = 0

    for j in jobs:
        remote = False
        if j['Location'] is not None:
            validate_loc = get_loc_from_string(j['Location'])
        else:
            j['Location'] = 'Remote'
            validate_loc = get_loc_from_string(j['Location'])

        if validate_loc is not None:
            if len(validate_loc) > 1:
                loc_list = validate_loc[1]
                for loc in loc_list:
                    if 'temporarily remote' in loc:
                        loc = validate_loc[0]
                        remote = True

                    location = get_location_from_string(loc)

                    if location is None:
                        locations = Location(name=loc)
                        locations.save()

                        locationAls = get_location_alias_from_string(loc)
                        if locationAls is None:
                            locationAlias = LocationAlias(name=loc, location=locations)
                            locationAlias.save()

                    else:
                        locationAls = get_location_alias_from_string(loc)
                        if locationAls is None:
                            locationAlias = LocationAlias(name=loc, location=location)
                            locationAlias.save()
            else:
                if 'Remote' in validate_loc[0]:
                    remote = True

                else:
                    location = get_location_from_string(validate_loc[0])

                    if location is None:
                        locations = Location(name=validate_loc[0])
                        locations.save()

                        locationAls = get_location_alias_from_string(validate_loc[0])
                        if locationAls is None:
                            locationAlias = LocationAlias(name=validate_loc[0], location=locations)
                            locationAlias.save()

                    else:
                        locationAls = get_location_alias_from_string(validate_loc[0])
                        if locationAls is None:
                            locationAlias = LocationAlias(name=validate_loc[0], location=location)
                            locationAlias.save()

        if len(validate_loc) > 1:
            if 'Remote' in validate_loc[0]:
                remote = True

            if 'temporarily remote' in validate_loc[1][0]:
                remote = True
                if validate_loc[0] is not None:
                    loc = validate_loc[0]
            else:
                if 'Remote' in validate_loc[0]:
                    remote = True

                if validate_loc[0] is not None:
                    loc = validate_loc[1][0]
                    location = get_location_from_string(loc)
                    employer = get_employer_from_string(j['Company_name'])
                    if employer is None:
                        employer = Employer(name=j['Company_name'], location=location)
                        employer.save()
        else:
            if 'Remote' in validate_loc[0]:
                remote = True

            location = get_location_from_string(validate_loc[0])
            employer = get_employer_from_string(j['Company_name'])
            if employer is None:
                employer = Employer(name=j['Company_name'], location=location)
                employer.save()

        position = get_position_from_string(j['Searched_job'])
        if position is None:
            position = Position(name=j['Searched_job'])
            position.save()

            positionAlias = PositionAlias(name=j['Searched_job'], position=position)
            positionAlias.save()

        employer = get_employer_from_string(j['Company_name'])

        (min_salary, max_salary, salary_str, tags) = get_salary_format(platform, j['Salary'], j['Tags'])
        if tags is not None:
            for tag in tags:
                t = tag.replace(' ', '-').lower()
                tagsave = get_tag_from_string(t)
                if tagsave is None:
                    Tag.objects.create(slug=t)

        validate = validate_diplicate_job(j['Job_title'], employer)
        if validate is None:
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

            validate_loc = get_loc_from_string(j['Location'])
            if len(validate_loc) > 1:
                loc_list = validate_loc[1]
                for loc in loc_list:
                    if 'temporarily remote' in loc:
                        loc = validate_loc[0]

                    location = get_location_from_string(loc)
                    if location is not None:
                        job.locations.add(location)
            else:
                location = get_location_from_string(validate_loc[0])
                if location is not None:
                    job.locations.add(location)

            if tags is not None:
                for tag in tags:
                    _tag = get_tag_from_string(tag)
                    if _tag is not None:
                        job.tags.add(_tag)

            new_jobs = new_jobs + 1

    spider.status = 'SYNCHED'
    spider.sync_desc = f"The spider's career ended successfully. Added {new_jobs} new jobs to {spider.name} at " + str(
        datetime.now())
    spider.save()


def fetch_sync_all_data(spider):
    if spider is None:
        raise Exception('First you must specify a spider')

    res = fetch_to_api(spider)
    data_jobs = fetch_data_to_json(spider, res)
    print('data_jobs', data_jobs)
    prub = []
    if len(data_jobs) > 0:
        for item_jobs in data_jobs:
            jobs = item_jobs['jobs']
            prub.append(item_jobs['num_job'])

        save_data(spider, jobs)

        if len(prub) > 0:
            spider.zyte_job_number = prub[0]
            spider.zyte_last_fetch_date = datetime.now()
            spider.save()

    return res


def parse_date(job):

    if job is None:
        raise Exception('First you must specify a job')

    job.published_date_processed = get_date_from_string(job.published_date_raw)
    job.save()

    return job


def get_salary_format(*args):
    (platform, salary, tags) = args
    min_salary = 0
    max_salary = 0
    salary_str = 'Not supplied'
    if 'getonboard' in platform:
        tags = tags
        if salary is not None and salary != 'Not supplied' and salary != 'Remote':
            salary = get_salary_from_string(salary)
            if salary:
                min_salary = float(salary[0]) * 12
                max_salary = float(salary[1]) * 12
                salary_str = f'${min_salary} - ${max_salary} a year.'
    else:
        tags = ['web-developer']

        if salary is not None and salary != 'Not supplied':
            salary = get_salary_from_string(salary)
            if salary:
                min_salary = float(salary[0])
                max_salary = float(salary[1])
                salary_str = f'${min_salary} - ${max_salary} a year.'

    return (min_salary, max_salary, salary_str, tags)


def list_to_tuple(params, item):

    if item is not None:
        OUTPUTS = []
        tup_ = params
        list_ = list(tup_)
        item_ = item

        for i in item_:
            list_.append(i)

    params = tuple(list_)

    return params


def get_position_from_string(keyword: str):
    alias = PositionAlias.objects.filter(name__iexact=keyword).first()

    if alias is None:
        return None

    return alias.position


def get_location_alias_from_string(keyword: str):
    localias = LocationAlias.objects.filter(name__iexact=keyword).first()

    if localias is None:
        return None

    return localias


def get_location_from_string(keyword: str):
    loc = Location.objects.filter(name__iexact=keyword).first()

    if loc is None:
        return None

    return loc


def get_location_alias_to_location_from_string(keyword: str):
    loc = LocationAlias.objects.filter(name__iexact=keyword).first()

    if loc is None:
        return None

    return loc.location


def get_employer_from_string(keyword: str):
    employer = Employer.objects.filter(name__iexact=keyword).first()

    if employer is None:
        return None

    return employer


def get_tag_from_string(keyword: str):
    tag = Tag.objects.filter(slug__iexact=keyword).first()

    if tag is None:
        return None

    return tag


def get_job_from_string(keyword: str):
    job = Job.objects.filter(apply_url__iexact=keyword).first()

    if job is None:
        return None

    return job


def get_tag_from_string(keyword: str):
    tag = Tag.objects.filter(slug__iexact=keyword).first()

    if tag is None:
        return None

    return tag


def validate_diplicate_job(job: str, employer):
    job = Job.objects.filter(title__iexact=job).first()
    employer = Job.objects.filter(employer=employer).first()

    if job is None and employer is None:
        return None

    return True


def get_split(value):
    result = value.split('/')
    return result


def days_ago_to_date(findings, string_date):
    number_of_days = int(findings.pop())
    _datetime = datetime.now() - timedelta(days=number_of_days)
    return _datetime


def today(findings, string_date):
    _datetime = datetime.now()
    return _datetime


def fetch_id_job_strin_to_list(findings, string_loc):
    job_id_fecth = list(findings.pop())
    return job_id_fecth


def loc(findings, string_loc):
    job_id_fecth = list(findings.pop())
    v = ''.join(job_id_fecth[1])
    v = v.replace(' o ', ',').replace(';', ',').strip()
    result = v.split(',')
    _res = []
    for tag in result:
        _res.append(tag.replace(' o ', ',').replace(';', ',').strip())

    location = job_id_fecth[0]
    loc = [location]
    loc.insert(len(loc), _res)

    return loc


def change_format_to_date(findings, string_date):
    job_id_fecth = findings
    _datetime = datetime.strptime(job_id_fecth[0], '%B %d, %Y')
    return _datetime


def format_corret_to_date(findings, string_date):
    return string_date


def remote_to_strin(findings, string_loc):
    if '.' in string_loc:
        string_loc = 'Remote'
    elif ')' in string_loc:
        string_loc = 'Remote'
    elif '(' in string_loc:
        string_loc = 'Remote'
    elif '' in string_loc:
        string_loc = 'Remote'

    remote = [string_loc.strip()]
    return remote


def salary(findings, string_salary):
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').replace(',', '').strip()]

    return val


def salary_month(findings, string_salary):
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').strip()]

    return val


def salary_month_only_one(findings, string_salary):
    salary = findings
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').replace(',', '').strip()]

    val += '0'
    return val


_cases = {
    '^(?:Active\s)?(\d{1,2})\+? days? ago': days_ago_to_date,
    '^(\d{1,4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})$': format_corret_to_date,
    '(.*\s?\d{1,2}\+?,? \d{1,4})': change_format_to_date,
    '^today': today,
    '^Just posted': today,
    '^just posted': today,
}

_cases_loc = {
    '(.*\s)?\((.*)\)': loc,
    '^\s?(.*)': remote_to_strin,
}

_cases_job_id = {
    '^(\d{1,9})\/(\d{1,3})\/(\d{1,3})$': fetch_id_job_strin_to_list,
}

_cases_to = {
    '^(.*)\s?-\s(.*)\+? a? year': salary,
    '^(.*)\s?to\s(.*)\+? per? year': salary,
    '^(.*)\s?-\s(.*)\+? USD/month': salary_month,
    '^(.*)\s?\+? USD/month': salary_month_only_one,
}


def get_date_from_string(string_date):
    for regex in _cases:
        findings = re.findall(regex, string_date)
        if isinstance(findings, list) and len(findings) > 0:
            return _cases[regex](findings, string_date)
    return None


def get_salary_from_string(string_salary):
    for regex in _cases_to:
        findings = re.findall(regex, string_salary)
        if isinstance(findings, list) and len(findings) > 0:
            return _cases_to[regex](findings, string_salary)
    return None


def get_loc_from_string(string_loc):
    for regex in _cases_loc:
        findings = re.findall(regex, string_loc)
        if isinstance(findings, list) and len(findings) > 0:
            return _cases_loc[regex](findings, string_loc)


def get_job_id_from_string(string_job):
    for regex in _cases_job_id:
        findings = re.findall(regex, string_job)
        if isinstance(findings, list) and len(findings) > 0:
            return _cases_job_id[regex](findings, string_job)
    return None
