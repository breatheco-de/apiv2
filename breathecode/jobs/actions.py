import requests, os, logging
from .models import Platform, Spider, Job, Employer, Position, PositionAlias, Tag, Location, LocationAlias

logger = logging.getLogger(__name__)

# ZYTE_API_DEPLOY = os.environ.get('ZYTE_API_DEPLOY')
# ZYTE_API_KEY = os.environ.get('ZYTE_API_KEY')


def run_spider(spider):
    """ This method run spider for a given position on admin"""
    #result = f'curl -u {spider.ZYTE_API_KEY}: https://app.scrapinghub.com/api/run.json -d project={spider.ZYTE_API_DEPLOY} -d spider={spider.platform.name} -d job={spider.job} -d loc={spider.loc}'
    # curl -u d62b44e4e9934393b54c679b5fcb001b: https://app.scrapinghub.com/api/run.json -d project=570286 -d spider=indeed -d job=javascript -d loc=remote

    data = {
        'project': spider.ZYTE_API_DEPLOY,
        'spider': spider.platform.name,
        'job': spider.job,
        'loc': spider.loc
    }

    response = requests.post('https://app.scrapinghub.com/api/run.json',
                             data=data,
                             auth=(spider.ZYTE_API_KEY, ''))

    # print('spider', result)


def fetch_spider_data(spider):
    _continue = True
    name_spider = spider.id
    spider.status = 'PENDING'
    spider.save()

    # job_number = job_number + 1

    response = requests.get(
        f'https://storage.scrapinghub.com/items/{spider.ZYTE_API_DEPLOY}/{spider.zyte_spider_number}/{spider.zyte_job_number}?apikey={spider.ZYTE_API_KEY}&format=json'
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
                       platform=spider.platform,
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
    """ Fetch sync all spiders"""
    # curl -u d62b44e4e9934393b54c679b5fcb001b: "https://app.scrapinghub.com/api/jobs/list.json?project=570286&spider=indeed&state=finished&count=10"

    params = (
        ('project', spider.ZYTE_API_DEPLOY),
        ('spider', spider.platform.name),
        ('state', 'finished'),
        ('count', spider.ZYTE_FETCH_COUNT),
    )

    res = requests.get('https://app.scrapinghub.com/api/jobs/list.json',
                       params=params,
                       auth=(spider.ZYTE_API_KEY, '')).json()

    i = 0

    while i < res['count']:
        if res['jobs'][i]['items_scraped'] > 0:
            spider.status = 'PENDING'
            spider.save()
            _num_spider = res['jobs'][i]['id']
            # _spider = Platform.objects.filter(name__iexact=res['jobs'][i]['spider']).first()

            response = requests.get(
                f'https://storage.scrapinghub.com/items/{_num_spider}?apikey={spider.ZYTE_API_KEY}&format=json'
            )

            if response.status_code != 200:
                raise Exception(
                    f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {_num_spider}'
                )
            elif response.status_code == 404:
                break

            jobs = response.json()
            # print('jobs', jobs)

            for j in jobs:

                if get_position_from_string(j['Searched_job']) is None:
                    _position = Position()
                    _position.name = j['Searched_job']
                    _position.save()

                    _positionAlias = PositionAlias()
                    _positionAlias.name = j['Searched_job']
                    _positionAlias.position = _position
                    _positionAlias.save()

                if get_location_from_string(j['Location']) is None:

                    if j['Location'] is None or j['Location'] == '.' or j['Location'] == '(' or j[
                            'Location'] == ' ':

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

                _remote = False

                if j['Location'] == 'Remote' or j['Location'] == 'remote':
                    _remote = True

                if get_job_from_string(j['Apply_to']) is None:
                    _job = Job(title=j['Job_title'],
                               platform=spider.platform,
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

        i = i + 1


def get_position_from_string(keyword: str):
    alias = PositionAlias.objects.filter(name__iexact=keyword).first()

    if alias is None:
        return None

    return alias.position


def get_location_from_string(keyword: str):
    loc = LocationAlias.objects.filter(name__iexact=keyword).first()

    if loc is None:
        return None

    return loc.location


def get_employer_from_string(keyword: str):
    employer = Employer.objects.filter(name__iexact=keyword).first()

    if employer is None:
        return None

    return employer


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


def get_split(value):
    result = value.split('/')
    return result
