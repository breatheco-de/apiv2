import logging, json, os, re
from breathecode.utils.validation_exception import ValidationException
from django.db.models import Q
from urllib.parse import urlparse
from slugify import slugify
from breathecode.utils import APIException
from breathecode.authenticate.models import CredentialsGithub
from .models import Asset, AssetTranslation, AssetTechnology, AssetAlias
from github import Github

logger = logging.getLogger(__name__)


def create_asset(data, asset_type, force=False):
    slug = data['slug']
    created = False

    aa = AssetAlias.objects.filter(slug=slug).first()
    if aa is not None and not force:
        raise APIException('Asset with this alias ' + slug + ' alrady exists')
    elif aa is not None and asset_type != aa.asset.asset_type:
        raise APIException(
            f'Cannot override asset {slug} because it already exists as a different type {aa.asset.asset_type}'
        )

    a = Asset.objects.filter(slug=slug).first()
    if a is None:
        a = Asset(slug=slug, asset_type=asset_type)
        created = True
        logger.debug(f'Adding asset project {a.slug}')
    else:
        logger.debug(f'Updating asset project {slug}')

    a.title = data['title']

    if 'repository' in data:
        a.url = data['repository']

    if 'readme' in data:
        a.readme_url = data['readme']

    if 'intro' in data:
        a.intro_video_url = data['intro']

    if 'language' in data:
        a.lang = data['language']
    elif 'lang' in data:
        a.lang = data['lang']

    if 'description' in data:
        a.description = data['description']

    if 'status' in data:
        a.status = data['status'].upper()

    if 'duration' in data:
        a.duration = data['duration']
    if 'solution_url' in data:
        a.duration = data['solution']
    if 'difficulty' in data:
        a.difficulty = data['difficulty'].upper()
    if 'graded' in data:
        a.graded = (data['graded'] == True or (isinstance(data['graded'], str)
                                               and data['graded'].upper() in ['ISOLATED', 'INCREMENTAL']))
    if 'video-id' in data:
        a.solution_video_url = 'https://www.youtube.com/watch?v=' + str(data['video-id'])
    if 'preview' in data:
        a.preview = data['preview']
    if 'video-solutions' in data:
        a.with_solutions = data['video-solutions']

    if 'authors_username' in data:
        authors = get_user_from_github_username(data['authors_username'])
        if len(authors) > 0:
            a.author = authors.pop()
            a.save()

    a.save()

    if 'translations' in data:
        for lan in data['translations']:
            if lan == 'en':
                lan = 'us'  # english is really USA
            l = AssetTranslation.objects.filter(slug=lan).first()
            if l is not None:
                if a.translations.filter(slug=lan).first() is None:
                    a.translations.add(l)
            else:
                logger.debug(f'Ignoring language {lan} because its not added as a possible AssetTranslation')

    if 'tags' in data:
        for tech in data['tags']:
            t = AssetTechnology.objects.filter(slug=tech).first()
            if t is None:
                t = AssetTechnology(slug=tech, title=tech)
                t.save()

            if a.technologies.filter(slug=tech).first() is None:
                a.technologies.add(t)

    return a, created


def get_user_from_github_username(username):
    authors = username.split(',')
    github_users = []
    for _author in authors:
        u = CredentialsGithub.objects.filter(username=_author).first()
        if u is not None:
            github_users.append(u.user)
    return github_users


def sync_with_github(asset_slug, author_id=None):

    logger.debug(f'Sync with github asset {asset_slug}')
    try:

        asset = Asset.objects.filter(slug=asset_slug).first()
        if asset is None:
            raise Exception(f'Asset with slug {asset_slug} not found when attempting to sync with github')

        if asset.owner is not None:
            author_id = asset.owner.id

        if author_id is None:
            raise Exception(
                f'System does not know what github credentials to use to retrive asset info for: {asset_slug}'
            )

        credentials = CredentialsGithub.objects.filter(user__id=author_id).first()
        if credentials is None:
            raise Exception(
                f'Github credentials for this user {author_id} not found when sync asset {asset_slug}')

        g = Github(credentials.token)
        if asset.asset_type == 'LESSON':
            asset = sync_github_lesson(g, asset)
        else:
            asset = sync_learnpack_asset(g, asset)

        asset.status_text = 'Successfully Synched'
        asset.status = 'OK'
        asset.save()
        logger.debug(f'Successfully re-synched asset {asset_slug} with github')
    except Exception as e:
        asset.status_text = str(e)
        asset.status = 'ERROR'
        asset.save()
        logger.error(f'Error updating {asset.url} from github: ' + str(e))

    return asset.status


def get_url_info(url: str):
    parts = urlparse(url).path[1:].split('/')
    org_name = parts[0]
    repo_name = parts[1]

    return org_name, repo_name


def sync_github_lesson(github, asset):

    org_name, repo_name = get_url_info(asset.url)
    repo = github.get_repo(f'{org_name}/{repo_name}')

    file_name = os.path.basename(asset.readme_url)

    result = re.search(r'\/blob\/([\w\d_\-]+)\/(.+)', asset.readme_url)
    if result is None:
        raise Exception('Invalid Github URL for asset ' + asset.slug + '.')

    branch, file_path = result.groups()
    logger.debug(f'Fetching markdown readme: {file_path}')
    asset.readme = repo.get_contents(file_path).content

    if org_name == 'breatheco-de' and repo_name == 'content':
        readme = asset.get_readme()
        logger.debug(f'Markdown is coming from breathecode/content, replacing images')
        base_url = os.path.dirname(asset.readme_url)
        replaced = re.sub(r'(["\'(])\.\.\/\.\.\/assets\/images\/([_\w\-\.]+)(["\')])',
                          r'\1' + base_url + r'/../../assets/images/\2?raw=true\3', readme['decoded'])
        asset.set_readme(replaced)

    return asset


def sync_learnpack_asset(github, asset):

    org_name, repo_name = get_url_info(asset.url)
    repo = github.get_repo(f'{org_name}/{repo_name}')

    readme_file = repo.get_contents('README.md')
    learn_file = None
    try:
        learn_file = repo.get_contents('learn.json')
    except:
        try:
            learn_file = repo.get_contents('.learn/learn.json')
        except:
            try:
                learn_file = repo.get_contents('bc.json')
            except:
                try:
                    learn_file = repo.get_contents('.learn/bc.json')
                except:
                    raise Exception('No configuration learn.json or bc.json file was found')

    asset.readme = str(readme_file.content)

    if learn_file is not None:
        config = json.loads(learn_file.decoded_content.decode('utf-8'))
        asset.config = config
        if 'title' in config:
            asset.title = config['title']
        if 'description' in config:
            asset.description = config['description']

        if 'preview' in config:
            asset.preview = config['preview']
        else:
            raise Exception(f'Missing preview URL')

        if 'video-id' in config:
            asset.solution_video_url = 'https://www.youtube.com/watch?v=' + str(config['video-id'])
            asset.with_video = True

        if 'duration' in config:
            asset.duration = config['duration']
        if 'difficulty' in config:
            asset.difficulty = config['difficulty']
        if 'solution' in config:
            asset.solution = config['solution']
            asset.with_solutions = True

        if 'language' in config:
            asset.lang = config['language']
        elif 'syntax' in config:
            asset.lang = config['syntax']

        if 'translations' in config:
            for lang in config['translations']:
                if lang == 'en':
                    lang = 'us'

                language = AssetTranslation.objects.filter(slug__iexact=lang).first()
                if language is None:
                    raise Exception(f"Language '{lang}' not found")
                asset.translations.add(language)

        if 'technologies' in config:
            for tech_slug in config['technologies']:
                _slug = slugify(tech_slug)
                technology = AssetTechnology.objects.filter(slug__iexact=_slug).first()
                if technology is None:
                    technology = AssetTechnology(slug=_slug, title=tech_slug)
                    technology.save()
                asset.technologies.add(technology)
    return asset


def test_asset(asset):
    if asset.asset_type == 'LESSON':
        test_lesson(asset)

    # TODO: add more tests for other types of assets
    return True


def test_lesson(lesson):
    from bs4 import BeautifulSoup
    import requests

    def test_url(url):
        response = requests.head(url, allow_redirects=False)
        if response.status_code not in [200, 302]:
            raise Exception('Invalid URL: ' + url)

    RELATIVE_IMAGES = r'(["\'(])\.\.\/\.\.\/assets\/images\/([_\w\-\.]+)(["\')])'
    readme = lesson.get_readme(parse=True)
    found_relative_images = re.match(RELATIVE_IMAGES, readme['decoded'])
    if found_relative_images:
        raise Exception(f'Found {len(found_relative_images)} relative images')

    soup = BeautifulSoup(readme['html'], features='lxml')
    anchors = soup.findAll('a')
    images = soup.findAll('img')
    for a in anchors:
        test_url(a.get('href'))
    for img in images:
        test_url(img.get('src'))
    return True


def test_syllabus(syl):

    if 'days' not in syl:
        raise ValidationException("Syllabus must have a 'days' or 'modules' property")

    def validate(type, day):
        if type not in day:
            raise ValidationException(f'Missing {type} property on module {count}')
        for a in day[type]:
            exists = AssetAlias.objects.filter(Q(slug=a['slug']) | Q(asset__slug=a['slug'])).first()
            if exists is None:
                raise ValidationException(f'Missing {type} with slug {a["slug"]} on module {count}')

    count = 0
    for day in syl['days']:
        count += 1
        validate('lessons', day)
        validate('quizzes', day)
        validate('replits', day)
        validate('projects', day)

        if 'teacher_instructions' not in day or day['teacher_instructions'] == '':
            raise ValidationException(f'Empty teacher instructions on module {count}')
