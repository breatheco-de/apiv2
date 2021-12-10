import requests, os, logging
from .models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias, ZyteProject

import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ZYTE_API_DEPLOY = os.environ.get('ZYTE_API_DEPLOY')
# ZYTE_API_KEY = os.environ.get('ZYTE_API_KEY')


def run_spider(spider):
    """ This method run spider for a given position on admin"""
    #result = f'curl -u {spider.ZYTE_API_KEY}: https://app.scrapinghub.com/api/run.json -d project={spider.zyte_api_deploy} -d spider={spider.platform.name} -d job={spider.job} -d loc={spider.loc}'
    # curl -u d62b44e4e9934393b54c679b5fcb001b: https://app.scrapinghub.com/api/run.json -d project=570286 -d spider=indeed -d job=javascript -d loc=remote
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

    response = requests.post('https://app.scrapinghub.com/api/run.json',
                             data=data,
                             auth=(spider.zyte_project.zyte_api_key, ''))

    return response


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
                       published=j['Post_date'],
                       apply_url=j['Apply_to'],
                       salary=j['Salary'],
                       remote=_remote,
                       employer=get_employer_from_string(j['Company_name']),
                       position=get_position_from_string(j['Searched_job']),
                       tag=get_tag_from_string(''),
                       location=get_location_from_string(j['Location']))

            _job.save()

    spider.status = 'SYNCHED'
    spider.save()

    return spider


def fetch_sync_all_data(spider):
    # print('Plataforma ', spider.zyte_project.platform.name)
    """ Fetch sync all spiders"""
    # curl -u d62b44e4e9934393b54c679b5fcb001b: "https://app.scrapinghub.com/api/jobs/list.json?project=570286&spider=indeed&state=finished&count=10"

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

    i = 0

    # print(res)
    _prub = []
    while i < res['count']:
        if res['jobs'][i]['items_scraped'] > 0:

            spider.status = 'PENDING'
            spider.save()
            _num_spider = res['jobs'][i]['id']
            # _spider = Platform.objects.filter(name__iexact=res['jobs'][i]['spider']).first()
            _num_spid = get_date_from_string(_num_spider)
            # _num_job = get_date_from_string(_num_spider)
            # print(_num_spid[0])
            # print(int(spider.zyte_spider_number))
            # print(type(_num_job))
            if int(_num_spid[1]) == int(spider.zyte_spider_number):
                # print('mayor a 2', _num_spid[1])
                if int(_num_spid[2]) >= spider.zyte_job_number:
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

                    print('jobs', jobs)

                    for j in jobs:

                        _position = get_position_from_string(j['Searched_job'])

                        if _position is None:
                            _position = Position()
                            _position.name = j['Searched_job']
                            _position.save()

                            _positionAlias = PositionAlias()
                            _positionAlias.name = j['Searched_job']
                            _positionAlias.position = _position
                            _positionAlias.save()

                        _location = get_location_alias_from_string(j['Location'])
                        print('_location alias init ', _location)
                        if _location is None:
                            _location = get_location_from_string(j['Location'])
                            print('_location init ', _location)
                            if _location is None:
                                _location = Location()
                                _location.name = j['Location']
                                _location.save()

                                _locationAlias = LocationAlias()
                                _locationAlias.name = j['Location']
                                _locationAlias.location = _location
                                _locationAlias.save()
                            else:
                                _locationAls = get_location_alias_from_string(j['Location'])
                                if _locationAls is None:
                                    print('_locationAls alias', _locationAls)

                                    print('_location to alias', _location.id)
                                    _locationAlias = LocationAlias()
                                    _locationAlias.name = j['Location']
                                    _locationAlias.location = _location
                                    _locationAlias.save()
                                else:
                                    _location = get_location_alias_to_location_from_string(j['Location'])
                        else:
                            _location = get_location_alias_to_location_from_string(j['Location'])

                        _employer = get_employer_from_string(j['Company_name'])
                        if _employer is None:
                            _employer = Employer()
                            _employer.name = j['Company_name']
                            _employer.save()

                        _remote = False

                        if j['Location'] == 'Remote' or j['Location'] == 'remote' or j[
                                'Location'] == 'Temporarily Remote' or j['Location'] == '(' or j[
                                    'Location'] == '.':
                            _remote = True

                        _validate = validate_diplicate_job(j['Job_title'], _employer)

                        _tag = Tag.objects.filter(slug__iexact='web-developer').first()

                        if _validate is None:
                            _job = Job(title=j['Job_title'],
                                       platform=spider.zyte_project.platform,
                                       published=j['Post_date'],
                                       apply_url=j['Apply_to'],
                                       salary=j['Salary'],
                                       remote=_remote,
                                       employer=_employer,
                                       position=_position,
                                       tag=_tag,
                                       location=_location)

                            _job.save()

                    spider.status = 'SYNCHED'
                    spider.save()

        i = i + 1
    # print(_prub[0])
    if len(_prub) > 0:
        spider.zyte_job_number = _prub[0]
        spider.zyte_last_fetch_date = datetime.now()
        spider.save()

    return spider


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


def fetch_id_job_strin_to_list(findings, string_date):
    job_id_fecth = list(findings.pop())
    return job_id_fecth


_cases = {
    '^(?:Active\s)?(\d{1,2})\+? days? ago': days_ago_to_date,
    '^(\d{1,9})\/(\d{1,3})\/(\d{1,3})$': fetch_id_job_strin_to_list,
    '^today': today,
    '^just posted': today,
}


def get_date_from_string(string_date):
    for regex in _cases:
        findings = re.findall(regex, string_date)
        if isinstance(findings, list) and len(findings) > 0:
            return _cases[regex](findings, string_date)
    return None


# def get_max_number(number):
#     n_mayor = 0
#     # k = 1
#     # c = int(number)

#     n = int(number)
#     if n > n_mayor:
#         n_mayor = n
#     else:
#         n_mayor = n_mayor
#         # k = k + 1

#     return n_mayor
# print("El mayor numero es: ",n_mayor)

# _input = "570286/2/33"
# _var = list(get_date_from_string(_input))
# print(int(_var[1]) + int(_var[2]))

# print(get_date_from_string(_input))
