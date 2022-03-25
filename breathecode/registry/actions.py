import logging, json, os, re
from breathecode.utils.validation_exception import ValidationException
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.template.loader import get_template
from urllib.parse import urlparse
from slugify import slugify
from breathecode.utils import APIException
from breathecode.assessment.models import Assessment
from breathecode.assessment.actions import create_from_json
from breathecode.authenticate.models import CredentialsGithub
from .models import Asset, AssetTechnology, AssetAlias, AssetErrorLog
from .serializers import AssetBigSerializer
from .utils import LessonValidator, ExerciseValidator, QuizValidator, AssetException, ProjectValidator
from github import Github

logger = logging.getLogger(__name__)


def generate_external_readme(a):

    if not a.external:
        return False

    readme = get_template('new_window.md')
    a.set_readme(readme.render(AssetBigSerializer(a).data))
    a.save()
    return True


def create_asset(data, asset_type, force=False):
    slug = data['slug']
    created = False

    aa = AssetAlias.objects.filter(slug=slug).first()
    if aa is not None and not force:
        raise APIException(f'Asset {asset_type} with this alias ' + slug + ' alrady exists')
    elif aa is not None and asset_type != aa.asset.asset_type:
        raise APIException(
            f'Cannot override asset {slug} because it already exists as a different type {aa.asset.asset_type}'
        )

    a = Asset.objects.filter(slug=slug).first()
    if a is None:
        a = Asset(slug=slug, asset_type=asset_type)
        created = True
        logger.debug(f'Adding asset {asset_type} {a.slug}')
    else:
        logger.debug(f'Updating asset {asset_type} {slug}')

    a.title = data['title']
    a.owner = User.objects.get(id=1)
    if a.asset_type in ['QUIZ', 'EXERCISE']:
        a.interactive = True
    if a.asset_type == 'EXERCISE':
        a.gitpod = True

    if 'tags' not in data:
        data['tags'] = []

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

    if a.lang == 'en':
        a.lang = 'us'  # english is really USA
    logger.debug(f'in language: {a.lang}')

    if 'technologies' in data:
        data['tags'] += data['technologies']

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

    if 'config' in data:
        a.config = data['config']

    if 'authors_username' in data:
        authors = get_user_from_github_username(data['authors_username'])
        if len(authors) > 0:
            a.author = authors.pop()

    _assessment = None
    if a.asset_type == 'QUIZ':
        _assessment = Assessment.objects.filter(slug=a.slug).first()
        if _assessment is None:
            _assessment = create_from_json(a.config)

        if _assessment.lang != a.lang:
            raise ValueError(
                f'Assessment found and quiz "{a.slug}" language don\'t share the same language {_assessment.lang} vs {a.lang}'
            )
        a.assessment = _assessment
        print(f'Assigned assessment {_assessment.slug} to asset {a.slug}')

    a.save()

    a.all_translations.add(a)  # add youself as a translation
    if 'translations' in data:
        for lan in data['translations']:
            if lan == 'en':
                lan = 'us'  # english is really USA

            is_translation = len(a.slug.split('.')) > 1
            original = Asset.objects.filter(slug=a.slug.split('.')[0]).first()

            # there is an original asset, it means "a" is a translation
            if original is not None and original.slug != a.slug:

                if _assessment is not None:
                    _assessment.original = original.assessment
                    _assessment.save()

                if original.all_translations.filter(slug=lan).first() is None:
                    logger.debug(
                        f'Adding translation {a.slug} for {lan} on previous original {original.slug}')
                    a.all_translations.add(original)
                else:
                    logger.debug(f'Ignoring language {lan} because the lesson already have a translation')

                a.slug.replace('.es', '-es')
                a.save()

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

        asset.status_text = 'Starting to sync...'
        asset.sync_status = 'PENDING'
        asset.save()

        if generate_external_readme(asset):
            asset.status_text = 'Readme file for external asset generated, not github sync'
            asset.sync_status = 'OK'
            asset.last_synch_at = None
            asset.save()
            return asset.sync_status

        if asset.owner is not None:
            author_id = asset.owner.id

        if author_id is None:
            raise Exception(
                f'System does not know what github credentials to use to retrive asset info for: {asset_slug}'
            )

        if asset.url is None or 'github.com' not in asset.url:
            raise Exception(f'Missing or invalid URL on {asset_slug}, it does not belong to github.com')

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
        asset.sync_status = 'OK'
        asset.last_synch_at = timezone.now()
        asset.save()
        logger.debug(f'Successfully re-synched asset {asset_slug} with github')
    except Exception as e:
        message = ''
        if hasattr(e, 'data'):
            message = e.data['message']
        else:
            message = str(e).replace('"', '\'')
        asset.status_text = str(message)
        asset.sync_status = 'ERROR'
        asset.save()
        logger.error(f'Error updating {asset.url} from github: ' + str(message))

    return asset.sync_status


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
        readme = asset.get_readme(parse=True)
        logger.debug(f'Markdown is coming from breathecode/content, replacing images')
        base_url = os.path.dirname(asset.readme_url)
        replaced = re.sub(r'(["\'(])\.\.\/\.\.\/assets\/images\/([_\w\-\.]+)(["\')])',
                          r'\1' + base_url + r'/../../assets/images/\2?raw=true\3', readme['decoded'])
        asset.set_readme(replaced)

        fm = dict(readme['frontmatter'].items())
        if 'slug' in fm and fm['slug'] != asset.slug:
            logger.debug(f'New slug {fm["slug"]} found for lesson {asset.slug}')
            asset.slug = fm['slug']

    return asset


def sync_learnpack_asset(github, asset):

    org_name, repo_name = get_url_info(asset.url)
    repo = github.get_repo(f'{org_name}/{repo_name}')

    lang = asset.lang
    if lang is None or lang == '':
        raise Exception('Language for this asset is not defined, imposible to retrieve readme')
    elif lang in ['us', 'en']:
        lang = ''
    else:
        lang = '.' + lang

    readme_file = None
    try:
        readme_file = repo.get_contents(f'README{lang}.md')
    except:
        raise Exception(f'Translation on README{lang}.md not found')

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
            asset.difficulty = config['difficulty'].upper()
        if 'solution' in config:
            asset.solution = config['solution']
            asset.with_solutions = True

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
    try:
        validator = None
        if asset.asset_type == 'LESSON':
            validator = LessonValidator(asset)
        elif asset.asset_type == 'EXERCISE':
            validator = ExerciseValidator(asset)
        elif asset.asset_type == 'PROJECT':
            validator = ProjectValidator(asset)
        elif asset.asset_type == 'QUIZ':
            validator = QuizValidator(asset)

        validator.validate()
        asset.status_text = 'Test Successfull'
        asset.test_status = 'OK'
        asset.last_test_at = timezone.now()
        asset.save()
        return True
    except AssetException as e:
        asset.status_text = str(e)
        asset.test_status = e.severity
        asset.save()
        raise e
    except Exception as e:
        asset.status_text = str(e)
        asset.test_status = 'ERROR'
        asset.save()
        raise e


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
