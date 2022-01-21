import requests, os, logging
from .models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject

import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ZYTE_API_DEPLOY = os.environ.get('ZYTE_API_DEPLOY')
# ZYTE_API_KEY = os.environ.get('ZYTE_API_KEY')


def run_spider(spider):
    """ This method run spider for a given position on admin"""
    # result = f'curl -u {spider.ZYTE_API_KEY}: https://app.scrapinghub.com/api/run.json -d project={spider.zyte_api_deploy} -d spider={spider.platform.name} -d job={spider.job} -d loc={spider.loc}'
    # curl -u d62b44e4e9934393b54c679b5fcb001b: https://app.scrapinghub.com/api/run.json -d project=570286 -d spider=indeed -d job=javascript -d loc=remote
    if spider is None:
        raise Exception('First you must specify a spider')

    if spider.job is None:
        raise Exception('First you must specify a job')

    _position = get_position_from_string(spider.job)

    if _position is None:
        _positionAlias = PositionAlias()
        _positionAlias.name = spider.job
        _positionAlias.position = spider.position
        _positionAlias.save()

    data = {
        'project': spider.zyte_project.zyte_api_deploy,
        'spider': spider.zyte_project.platform.name,
        'job': spider.job,
    }
    # rbl=New%20York%2C%20NY
    data['loc'] = spider.loc
    # data['jt'] = 'fulltime'
    valor = '1'
    int(valor)
    response = requests.post('https://app.scrapinghub.com/api/run.json',
                             data=data,
                             auth=(spider.zyte_project.zyte_api_key, ''))

    result = response.json()

    return (response.status_code == 200 and 'status' in result and result['status'] == 'ok', result)


def fetch_spider_data(spider):
    _continue = True
    name_spider = spider.id
    spider.status = 'PENDING'
    spider.save()

    # job_number = job_number + 1

    response = requests.get(
        f'https://storage.scrapinghub.com/items/{spider.zyte_project.zyte_api_deploy}/{spider.zyte_spider_number}/{spider.zyte_job_number}?apikey={spider.zyte_project.zyte_api_key}&format=json'
    )

    if response.status_code != 200:
        raise Exception(
            f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {spider.zyte_job_number}'
        )
    jobs = response.json()
    # print('jobs', jobs)

    if len(jobs) == 0:
        logger.debug(
            f'No more jobs found for spider {spider} {spider.zyte_spider_number} job {spider.zyte_job_number}'
        )
        _continue = False

    for j in jobs:
        # print('spider', spider)
        # print('Lugar', get_location_from_string(j['Location']))

        if get_position_from_string(j['Searched_job']) is None:
            _position = Position()
            _position.name = j['Searched_job']
            _position.save()

            _positionAlias = PositionAlias()
            _positionAlias.name = j['Searched_job']
            _positionAlias.position = _position
            _positionAlias.save()

        if get_location_from_string(j['Location']) is None:

            if j['Location'] is None or j['Location'] == '.' or j['Location'] == '(' or j['Location'] == ' ':

                j['Location'] = 'Remote'

            else:

                _location = Location()
                _location.name = j['Location']
                _location.save()

                _locationAlias = LocationAlias()
                _locationAlias.name = j['Location']
                _locationAlias.location = _location
                _locationAlias.save()

        if get_employer_from_string(j['Company_name']) is None:
            _employer = Employer()
            _employer.name = j['Company_name']
            _employer.save()

        # if get_employer_from_string(j['tag']) is not None:
        #     _tag = Tag(slug=j['tag'])
        #     _tag.save()

        _remote = False

        if j['Location'] == 'Remote' or j['Location'] == 'remote':
            _remote = True

        if get_job_from_string(j['Apply_to']) is None:
            _job = Job(title=j['Job_title'],
                       platform=spider.zyte_project.platform,
                       published_date_raw=j['Post_date'],
                       apply_url=j['Apply_to'],
                       salary=j['Salary'],
                       min_salary=j['Salary'],
                       max_salary=j['Salary'],
                       remote=_remote,
                       employer=get_employer_from_string(j['Company_name']),
                       position=get_position_from_string(j['Searched_job']),
                       tag=get_tag_from_string(''),
                       location=get_location_from_string(j['Location']))

            _job.save()

    spider.status = 'SYNCHED'
    spider.save()

    return spider


def fetch_to_api(spider):
    # print('Plataforma ', spider.zyte_project.platform.name)
    """ Fetch sync all spiders"""
    # curl -u d62b44e4e9934393b54c679b5fcb001b: "https://app.scrapinghub.com/api/jobs/list.json?project=570286&spider=indeed&state=finished&count=10"
    if spider is None:
        raise Exception('First you must specify a spider')

    params = (
        ('project', spider.zyte_project.zyte_api_deploy),
        ('spider', spider.zyte_project.platform.name),
        ('state', 'finished'),
    )

    _count = [('count', spider.zyte_fetch_count)]

    if spider.zyte_fetch_count > 0:
        list_to_tuple(params, _count)

    res = requests.get('https://app.scrapinghub.com/api/jobs/list.json',
                       params=params,
                       auth=(spider.zyte_project.zyte_api_key, '')).json()

    return res


def fetch_sync_all_data(spider):

    if spider is None:
        raise Exception('First you must specify a spider')

    res = fetch_to_api(spider)

    i = 0

    print(res)
    _prub = []
    new_jobs = 0
    while i < res['count']:
        if res['jobs'][i]['items_scraped'] > 0:

            platafom = spider.zyte_project.platform.name
            spider.status = 'PENDING'
            # spider.save()
            _num_spider = res['jobs'][i]['id']
            # _spider = Platform.objects.filter(name__iexact=res['jobs'][i]['spider']).first()
            _num_spid = get_loc_from_string(_num_spider)
            # _num_job = get_date_from_string(_num_spider)
            # print(_num_spid[0])
            # print(int(spider.zyte_spider_number))
            # print(type(_num_job))
            if int(_num_spid[1]) == int(spider.zyte_spider_number):
                # print('mayor a 2', _num_spid[1])
                if int(_num_spid[2]) >= int(spider.zyte_job_number):
                    # print('es mayor o igual a 33', _num_spid[2])
                    _prub.append(_num_spid[2])

                    response = requests.get(
                        f'https://storage.scrapinghub.com/items/{_num_spider}?apikey={spider.zyte_project.zyte_api_key}&format=json'
                    )

                    if response.status_code != 200:
                        raise Exception(
                            f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {_num_spider}'
                        )
                    elif response.status_code == 404:
                        break

                    jobs = response.json()
                    # print(jobs)

                    for j in jobs:
                        _remote = False
                        if j['Location'] is not None:
                            _validate_loc = get_loc_from_string(j['Location'])
                        else:
                            j['Location'] = 'Remote'
                            _validate_loc = get_loc_from_string(j['Location'])
                            # print('llego así: ', j['Location'])
                            # print('Modificado: ', _validate_loc)

                        if _validate_loc is not None:

                            if len(_validate_loc) > 1:

                                loc_list = _validate_loc[1]

                                for loc in loc_list:
                                    if 'temporarily remote' in loc:
                                        loc = _validate_loc[0]
                                        _remote = True

                                    _location = get_location_from_string(loc)

                                    if _location is None:
                                        _locations = Location()
                                        _locations.name = loc
                                        _locations.save()

                                        _locationAls = get_location_alias_from_string(loc)
                                        if _locationAls is None:
                                            _locationAlias = LocationAlias()
                                            _locationAlias.name = loc
                                            _locationAlias.location = _locations
                                            _locationAlias.save()

                                    else:
                                        _locationAls = get_location_alias_from_string(loc)
                                        if _locationAls is None:
                                            _locationAlias = LocationAlias()
                                            _locationAlias.name = loc
                                            _locationAlias.location = _location

                            else:

                                if 'Remote' in _validate_loc[0]:
                                    _remote = True

                                else:

                                    _location = get_location_from_string(_validate_loc[0])

                                    if _location is None:
                                        _locations = Location()
                                        _locations.name = _validate_loc[0]
                                        _locations.save()

                                        _locationAls = get_location_alias_from_string(_validate_loc[0])
                                        if _locationAls is None:
                                            _locationAlias = LocationAlias()
                                            _locationAlias.name = _validate_loc[0]
                                            _locationAlias.location = _locations
                                            _locationAlias.save()

                                    else:
                                        _locationAls = get_location_alias_from_string(_validate_loc[0])
                                        if _locationAls is None:
                                            _locationAlias = LocationAlias()
                                            _locationAlias.name = _validate_loc[0]
                                            _locationAlias.location = _location

                        if len(_validate_loc) > 1:

                            if 'Remote' in _validate_loc[0]:
                                _remote = True
                            # print('Base ', _validate_loc)
                            # print('mayor a uno ', _validate_loc[1][0])
                            if 'temporarily remote' in _validate_loc[1][0]:
                                # print('Location ', _validate_loc[0])
                                _remote = True
                                if _validate_loc[0] is not None:
                                    _loc = _validate_loc[0]
                            else:
                                if 'Remote' in _validate_loc[0]:
                                    _remote = True
                                # print('Location ', _validate_loc[1][0])
                                if _validate_loc[0] is not None:
                                    _loc = _validate_loc[1][0]

                                    _location = get_location_from_string(_loc)
                                    # print('retorno location ', _location)

                                    _employer = get_employer_from_string(j['Company_name'])
                                    if _employer is None:

                                        _employer = Employer()
                                        _employer.name = j['Company_name']
                                        _employer.location = _location
                                        _employer.save()
                        else:
                            if 'Remote' in _validate_loc[0]:
                                _remote = True
                            # print('Menor a uno ', _validate_loc[0])
                            _location = get_location_from_string(_validate_loc[0])
                            # print('retorno location menor a uno', _location)
                            _employer = get_employer_from_string(j['Company_name'])
                            if _employer is None:

                                _employer = Employer()
                                _employer.name = j['Company_name']
                                _employer.location = _location
                                _employer.save()

                        _position = get_position_from_string(j['Searched_job'])

                        if _position is None:
                            _position = Position()
                            _position.name = j['Searched_job']
                            _position.save()

                            _positionAlias = PositionAlias()
                            _positionAlias.name = j['Searched_job']
                            _positionAlias.position = _position
                            _positionAlias.save()

                        _employer = get_employer_from_string(j['Company_name'])
                        # print('employer', _employer)
                        _min_salary = 0
                        _max_salary = 0
                        _salary_str = 'Not supplied'
                        if 'getonboard' in platafom:
                            tags = j['Tags']
                            # print('salary===>', j['Salary'])
                            if j['Salary'] is not None and j['Salary'] != 'Not supplied' and j[
                                    'Salary'] != 'Remote':
                                _salary = get_salary_from_string(j['Salary'])
                                # print('no salary========>', _salary)
                                if _salary:
                                    _min_salary = float(_salary[0]) * 12
                                    _max_salary = float(_salary[1]) * 12
                                    _salary_str = f'${_min_salary} - ${_max_salary} a year.'
                                else:
                                    _salary_str = j['Salary']
                        else:
                            tags = ['web-developer']
                            # print('salary===>', j['Salary'])
                            if j['Salary'] is not None and j['Salary'] != 'Not supplied':
                                _salary = get_salary_from_string(j['Salary'])
                                if _salary:
                                    _min_salary = float(_salary[0])
                                    _max_salary = float(_salary[1])
                                    _salary_str = f'${_min_salary} - ${_max_salary} a year.'
                                else:
                                    _salary_str = j['Salary']

                        if tags is not None:
                            for tag in tags:
                                t = tag.replace(' ', '-').lower()
                                tagsave = get_tag_from_string(t)
                                if tagsave is None:
                                    Tag.objects.create(slug=t)
                                    # print(t)

                        _validate = validate_diplicate_job(j['Job_title'], _employer)
                        if _validate is None:
                            _job = Job(
                                title=j['Job_title'],
                                platform=spider.zyte_project.platform,
                                published_date_raw=j['Post_date'],
                                apply_url=j['Apply_to'],
                                salary=_salary_str,
                                min_salary=_min_salary,
                                max_salary=_max_salary,
                                remote=_remote,
                                employer=_employer,
                                position=_position,
                                #    tags=Job.tags.add(tag),
                                #    locations=Location().tags.add(loc)
                            )

                            _job.save()

                            _validate_loc = get_loc_from_string(j['Location'])
                            # print('_validate_loc ===>', _validate_loc)
                            if len(_validate_loc) > 1:
                                # print('Base ', _validate_loc)
                                # print('mayor a uno ', _validate_loc[1][0])
                                loc_list = _validate_loc[1]

                                for loc in loc_list:
                                    if 'temporarily remote' in loc:
                                        loc = _validate_loc[0]

                                    _location = get_location_from_string(loc)
                                    if _location is not None:

                                        _job.locations.add(_location)
                                        # _employer.save()
                            else:
                                # print('Menor a uno ', _validate_loc[0])
                                _location = get_location_from_string(_validate_loc[0])
                                if _location is not None:
                                    _job.locations.add(_location)

                            if tags is not None:
                                for tag in tags:
                                    _tag = get_tag_from_string(tag)
                                    if _tag is not None:

                                        _job.tags.add(_tag)
                                        # _employer.save()
                            new_jobs = new_jobs + 1
                    spider.status = 'SYNCHED'
                    spider.sync_desc = f"The spider's career ended successfully. Added {new_jobs} new jobs to {spider.name} at " + str(
                        datetime.now())
                    spider.save()

        i = i + 1
        # print(_prub[0])
    if len(_prub) > 0:
        spider.zyte_job_number = _prub[0]
        spider.zyte_last_fetch_date = datetime.now()
        spider.save()
    # new_jobs += new_jobs
    print(f'Added {new_jobs} new jobs to {spider.name}')

    return res


def parse_date(job):

    if job is None:
        raise Exception('First you must specify a job')

    if job.published_date_raw is None:
        raise Exception('Error: The job no has a publiched date')
    print('job ::: ', get_date_from_string(job.published_date_raw))

    job.published_date_processed = get_date_from_string(job.published_date_raw)
    job.save()

    return job


def tags_exitst(obj):
    if job is None:
        return ['web']
    return obj


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
    # job_id_fecth = string_date
    # _datetime = datetime.strptime(job_id_fecth, '%Y-%m-%d %H:%M:%S')
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

    _remote = [string_loc.strip()]
    return _remote


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
    '^(\d{1,9})\/(\d{1,3})\/(\d{1,3})$': fetch_id_job_strin_to_list,
    '(.*\s)?\((.*)\)': loc,
    '^\s?(.*)': remote_to_strin,
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


# _input = "July 17, 1977"
# print(get_date_from_string(_input))
# Active 6 days ago
# July 17, 1977
# Remote (chile)
# Remote (chile, Venezuela, Peru,colombia)
# Santiago (chile, Venezuela, Peru,colombia)
# 570286/2/33


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
    return None
