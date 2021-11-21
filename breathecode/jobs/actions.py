import requests, os, logging
from .models import Platform, Spider, Job, Employer, Position, Tag, Location

logger = logging.getLogger(__name__)

ZYTE_API_DEPLOY = os.environ.get('ZYTE_API_DEPLOY')
ZYTE_API_KEY = os.environ.get('ZYTE_API_KEY')


def fetch_spider_data(spider):
    _continue = True
    incoming_jobs = []
    job_number = spider.zyte_job_number
    name_spider = spider.id
    spider.status = 'PENDING'
    spider.save()

    # job_number = job_number + 1

    response = requests.get(
        f'https://storage.scrapinghub.com/items/{ZYTE_API_DEPLOY}/{spider.zyte_spider_number}/{job_number}?apikey={ZYTE_API_KEY}&format=json'
    )

    if response.status_code == 404:
        _continue = False

    elif response.status_code != 200:
        raise Exception(
            f'There was a {response.status_code} error fetching spider {spider.zyte_spider_number} job {job_number}'
        )
    jobs = response.json()
    # print('jobs', jobs)

    if len(jobs) == 0:
        logger.debug(f'No more jobs found for spider {spider.zyte_spider_number} job {job_number}')
        _continue = False

    for j in jobs:
        print(j['Company_name'])

        if j['Company_name'] == 0 or j['Company_name'] == '':
            _continue
        elif j['Company_name']:
            _emply = Employer(name=j['Company_name'])
            _emply.save()

        if j['Searched_job'] == 0 or j['Searched_job'] == '':
            _continue
        elif j['Searched_job']:
            _position = Position(name=j['Searched_job'])
            _position.save()

        if j['Searched_job'] == 0 or j['Searched_job'] == '':
            _continue
        elif j['Searched_job']:
            _tag = Tag(slug=j['Searched_job'])
            _tag.save()

        if j['Location'] == 0 or j['Location'] == '':
            _continue
        elif j['Location']:
            _loc = Location(city=j['Location'])
            _loc.save()

        _employe_last = Employer.objects.latest('id')
        _position_last = Position.objects.latest('id')
        _tag_last = Tag.objects.latest('id')
        _location_last = Location.objects.latest('id')

        _remote = False

        if j['Location'] == 'Remote' or j['Location'] == 'remote':
            _remote = True

        _job = Job(title=j['Job_title'],
                   published=j['Post_date'],
                   apply_url=j['Apply_to'],
                   salary=j['Salary'],
                   remote=_remote,
                   employer=_employe_last,
                   position=_position_last,
                   tag=_tag_last,
                   location=_location_last)

        # _job = Job(platform=_platform_last, )
        _job.save()

    spider.status = 'SYNCHED'
    spider.save()

    return spider
