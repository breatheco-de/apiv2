import base64, frontmatter, markdown, pathlib, logging, re, hashlib, json
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.template.loader import get_template
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event
from django.db.models import Q
from .signals import asset_slug_modified
from slugify import slugify
from breathecode.assessment.models import Assessment

__all__ = ['AssetTechnology', 'Asset', 'AssetAlias']
logger = logging.getLogger(__name__)

PUBLIC = 'PUBLIC'
UNLISTED = 'UNLISTED'
PRIVATE = 'PRIVATE'
VISIBILITY = (
    (PUBLIC, 'Public'),
    (UNLISTED, 'Unlisted'),
    (PRIVATE, 'Private'),
)


class AssetTechnology(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=2,
                            blank=True,
                            default=None,
                            null=True,
                            help_text='Leave blank if will be shown in all languages')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, default=None, blank=True, null=True)
    featured_asset = models.ForeignKey('Asset',
                                       on_delete=models.SET_NULL,
                                       default=None,
                                       blank=True,
                                       null=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)

    description = models.TextField(null=True, blank=True, default=None)
    icon_url = models.URLField(null=True, blank=True, default=None, help_text='Image icon to show on website')

    def __str__(self):
        return self.title

    @classmethod
    def get_or_create(cls, tech_slug):
        _slug = slugify(tech_slug).lower()
        technology = cls.objects.filter(slug__iexact=_slug).first()
        if technology is None:
            technology = cls(slug=_slug, title=tech_slug)
            technology.save()

        # Parent technologies will merge similar ones like: reactjs and react.js together.
        if technology.parent is not None:
            technology = technology.parent

        return technology


class AssetCategory(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')
    description = models.TextField(null=True, blank=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug


class KeywordCluster(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)
    is_deprecated = models.BooleanField(
        default=False,
        help_text=
        'Used when you want to stop using this cluster, all previous articles will be kept but no new articles will be assigned'
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug


class AssetKeyword(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')

    cluster = models.ForeignKey(KeywordCluster,
                                on_delete=models.SET_NULL,
                                default=None,
                                blank=True,
                                null=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug


PROJECT = 'PROJECT'
EXERCISE = 'EXERCISE'
LESSON = 'LESSON'
QUIZ = 'QUIZ'
VIDEO = 'VIDEO'
ARTICLE = 'ARTICLE'
TYPE = (
    (PROJECT, 'Project'),
    (EXERCISE, 'Exercise'),
    (QUIZ, 'Quiz'),
    (LESSON, 'Lesson'),
    (VIDEO, 'Video'),
    (ARTICLE, 'Article'),
)

BEGINNER = 'BEGINNER'
EASY = 'EASY'
DIFFICULTY = (
    (BEGINNER, 'Beginner'),
    (EASY, 'Easy'),
)

DRAFT = 'DRAFT'
UNASSIGNED = 'UNASSIGNED'
WRITING = 'WRITING'
PUBLISHED = 'PUBLISHED'
ASSET_STATUS = (
    (UNASSIGNED, 'Unassigned'),
    (WRITING, 'Writing'),
    (DRAFT, 'Draft'),
    (PUBLISHED, 'Published'),
)

ASSET_SYNC_STATUS = (
    ('PENDING', 'Pending'),
    ('ERROR', 'Error'),
    ('OK', 'Ok'),
    ('WARNING', 'Warning'),
)


class Asset(models.Model):
    def __init__(self, *args, **kwargs):
        super(Asset, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=2, blank=True, null=True, default=None, help_text='E.g: en, es, it')

    all_translations = models.ManyToManyField('self', blank=True)
    technologies = models.ManyToManyField(AssetTechnology)
    seo_keywords = models.ManyToManyField(AssetKeyword,
                                          blank=True,
                                          help_text='Optimize for a max of two keywords per asset')
    category = models.ForeignKey(AssetCategory,
                                 on_delete=models.SET_NULL,
                                 default=None,
                                 blank=True,
                                 null=True)

    url = models.URLField(null=True, blank=True, default=None)
    solution_url = models.URLField(null=True, blank=True, default=None)
    preview = models.URLField(null=True, blank=True, default=None)
    description = models.TextField(null=True, blank=True, default=None)
    requirements = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text='Brief for the copywriters, mainly used to describe what this lessons needs to be about')

    readme_url = models.URLField(
        null=True,
        blank=True,
        default=None,
        help_text=
        'This will be used to synch only lessons from github. Projects, quizzes and exercises it will try README.md for english and README.lang.md for other langs'
    )
    intro_video_url = models.URLField(null=True, blank=True, default=None)
    solution_video_url = models.URLField(null=True, blank=True, default=None)
    readme = models.TextField(null=True, blank=True, default=None)
    html = models.TextField(null=True, blank=True, default=None)

    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, null=True, default=None)

    config = models.JSONField(null=True, blank=True, default=None)

    external = models.BooleanField(
        default=False,
        help_text=
        'External assets will open in a new window, they are not built using breathecode or learnpack tecnology'
    )

    interactive = models.BooleanField(default=False)
    with_solutions = models.BooleanField(default=False)
    with_video = models.BooleanField(default=False)
    graded = models.BooleanField(default=False)
    gitpod = models.BooleanField(default=False)
    duration = models.IntegerField(null=True, blank=True, default=None, help_text='In hours')

    difficulty = models.CharField(max_length=20, choices=DIFFICULTY, default=None, null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)
    asset_type = models.CharField(max_length=20, choices=TYPE)

    status = models.CharField(max_length=20,
                              choices=ASSET_STATUS,
                              default=UNASSIGNED,
                              help_text='Related to the publishing of the asset')
    sync_status = models.CharField(max_length=20,
                                   choices=ASSET_SYNC_STATUS,
                                   default=None,
                                   null=True,
                                   blank=True,
                                   help_text='Internal state automatically set by the system based on sync')
    test_status = models.CharField(max_length=20,
                                   choices=ASSET_SYNC_STATUS,
                                   default=None,
                                   null=True,
                                   blank=True,
                                   help_text='Internal state automatically set by the system based on test')
    published_at = models.DateTimeField(null=True, blank=True, default=None)
    last_synch_at = models.DateTimeField(null=True, blank=True, default=None)
    last_test_at = models.DateTimeField(null=True, blank=True, default=None)
    status_text = models.TextField(null=True,
                                   default=None,
                                   blank=True,
                                   help_text='Used by the sych status to provide feedback')

    authors_username = models.CharField(max_length=80,
                                        null=True,
                                        default=None,
                                        blank=True,
                                        help_text='Github usernames separated by comma')
    assessment = models.ForeignKey(Assessment,
                                   on_delete=models.SET_NULL,
                                   default=None,
                                   blank=True,
                                   null=True,
                                   help_text='Connection with the assessment breathecode app')
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True,
                               help_text='Who wrote the lesson, not necessarily the owner')
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              related_name='owned_lessons',
                              default=None,
                              blank=True,
                              null=True,
                              help_text='The owner has the github premissions to update the lesson')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug}'

    def save(self, *args, **kwargs):

        # only validate this on creation
        if self.pk is None or self.__old_slug != self.slug:
            alias = AssetAlias.objects.filter(slug=self.slug).first()
            if alias is not None:
                raise Exception(f'New slug {self.slug} for {self.__old_slug} is already taken by alias')

            super().save(*args, **kwargs)
            self.__old_slug = self.slug
            asset_slug_modified.send(instance=self, sender=Asset)
        else:
            super().save(*args, **kwargs)

    def get_readme(self, parse=None, raw=False):

        if self.readme is None or self.readme == '':
            if self.asset_type != 'QUIZ':
                AssetErrorLog(slug=AssetErrorLog.EMPTY_README,
                              path=self.slug,
                              asset_type=self.asset_type,
                              asset=self,
                              status_text='Readme file was not found').save()
            self.set_readme(
                get_template('empty.md').render({
                    'title': self.title,
                    'lang': self.lang,
                    'asset_type': self.asset_type,
                }))

        if raw:
            return self.readme

        if self.readme_url is None and self.asset_type == 'LESSON':
            self.readme_url = self.url
            self.save()

        readme = {
            'raw': self.readme,
            'decoded': base64.b64decode(self.readme.encode('utf-8')).decode('utf-8')
        }
        if parse:
            # external assets will have a default markdown readme generated internally
            extension = '.md'
            if self.readme_url and self.readme_url != '':
                extension = pathlib.Path(self.readme_url).suffix if not self.external else '.md'

            if extension in ['.md', '.mdx', '.txt']:
                readme = self.parse(readme, format='markdown')
            elif extension in ['.ipynb']:
                readme = self.parse(readme, format='notebook')
            else:
                raise Exception('Uknown readme file extension ' + extension + ' for ' + self.asset_type +
                                ': ' + self.slug)
        return readme

    def parse(self, readme, format='markdown'):
        if format == 'markdown':
            _data = frontmatter.loads(readme['decoded'])
            readme['frontmatter'] = _data.metadata
            readme['frontmatter']['format'] = format
            readme['html'] = markdown.markdown(_data.content, extensions=['markdown.extensions.fenced_code'])
        if format == 'notebook':
            import nbformat
            from nbconvert import HTMLExporter
            notebook = nbformat.reads(readme['decoded'], as_version=4)
            # Instantiate the exporter. We use the `classic` template for now; we'll get into more details
            # later about how to customize the exporter further. You can use 'basic'
            html_exporter = HTMLExporter(template_name='basic')
            # Process the notebook we loaded earlier
            body, resources = html_exporter.from_notebook_node(notebook)
            readme['frontmatter'] = resources
            readme['frontmatter']['format'] = format
            readme['html'] = body
        return readme

    def set_readme(self, content):
        self.readme = str(base64.b64encode(content.encode('utf-8')).decode('utf-8'))
        return self

    def log_error(self, error_slug, status_text=None):
        error = AssetErrorLog(slug=error_slug,
                              asset=self,
                              asset_type=self.asset_type,
                              status_text=status_text,
                              path=self.slug)
        error.save()
        return error

    def get_tasks(self):

        if self.readme is None:
            return []

        regex = r'\-\s\[(?P<status>[\sxX-])\]\s(?P<label>.+)'
        findings = list(re.finditer(regex, self.get_readme()['decoded']))
        tasks = []
        while len(findings) > 0:
            task_find = findings.pop(0)
            task = task_find.groupdict()
            task['id'] = int(hashlib.sha1(task['label'].encode('utf-8')).hexdigest(), 16) % (10**8)
            task['status'] = 'DONE' if 'status' in task and task['status'].strip().lower(
            ) == 'x' else 'PENDING'

            tasks.append(task)
        return tasks

    @staticmethod
    def get_by_slug(asset_slug, request=None, asset_type=None):
        user = None
        if request is not None and not isinstance(request.user, AnonymousUser):
            user = request.user

        alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
        if alias is None:
            AssetErrorLog(slug=AssetErrorLog.SLUG_NOT_FOUND,
                          path=asset_slug,
                          asset_type=asset_type,
                          user=user).save()
            return None
        elif asset_type is not None and alias.asset.asset_type.lower() == asset_type.lower():
            AssetErrorLog(slug=AssetErrorLog.DIFFERENT_TYPE,
                          path=asset_slug,
                          asset=alias.asset,
                          asset_type=asset_type,
                          user=user).save()
        else:
            return alias.asset


class AssetAlias(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.slug


class AssetComment(models.Model):

    text = models.TextField()
    resolved = models.BooleanField(default=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True,
                               help_text='Who wrote the lesson, not necessarily the owner')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return 'AssetComment ' + str(self.id)


ERROR = 'ERROR'
FIXED = 'FIXED'
IGNORED = 'IGNORED'
ERROR_STATUS = (
    (ERROR, 'Error'),
    (FIXED, 'Fixed'),
    (IGNORED, 'Ignored'),
)


class AssetErrorLog(models.Model):
    SLUG_NOT_FOUND = 'slug-not-found'
    DIFFERENT_TYPE = 'different-type'
    EMPTY_README = 'empty-readme'
    INVALID_URL = 'invalid-url'
    README_SYNTAX = 'readme-syntax-error'

    asset_type = models.CharField(max_length=20, choices=TYPE, default=None, null=True, blank=True)
    slug = models.SlugField(max_length=200)
    status = models.CharField(max_length=20, choices=ERROR_STATUS, default=ERROR)
    path = models.CharField(max_length=200)
    status_text = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text='Status details, it may be set automatically if enough error information')
    user = models.ForeignKey(User,
                             on_delete=models.SET_NULL,
                             default=None,
                             null=True,
                             help_text='The user how asked for the asset and got the error')
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        help_text=
        'Assign an asset to this error and you will be able to create an alias for it from the django admin bulk actions "create alias"'
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f'Error {self.status} with {self.slug}'
