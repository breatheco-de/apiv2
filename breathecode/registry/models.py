import base64, frontmatter, markdown, pathlib, logging, re, hashlib, json
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser
from django.template.loader import get_template
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event
from django.db.models import Q
from .signals import asset_slug_modified, asset_readme_modified
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
SORT_PRIORITY = (
    (1, 1),
    (2, 2),
    (3, 3),
)


class AssetTechnology(models.Model):
    slug = models.SlugField(max_length=200,
                            unique=True,
                            help_text='Technologies are unified within all 4geeks.com')
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
    sort_priority = models.IntegerField(null=False,
                                        choices=SORT_PRIORITY,
                                        blank=False,
                                        default=3,
                                        help_text='Priority to sort technology (1, 2, or 3)')

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

    def __init__(self, *args, **kwargs):
        super(AssetCategory, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')
    description = models.TextField(null=True, blank=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    # Ideal for generating blog post thumbnails
    auto_generate_previews = models.BooleanField(default=False)
    preview_generation_url = models.URLField(null=True,
                                             blank=True,
                                             default=None,
                                             help_text='Will be POSTed to get preview image')

    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug
            cat = AssetCategory.objects.filter(slug=self.slug, academy=self.academy).first()
            if cat is not None:
                raise Exception(f'Category with slug {self.slug} already exists on this academy')

        super().save(*args, **kwargs)


class KeywordCluster(models.Model):

    def __init__(self, *args, **kwargs):
        super(KeywordCluster, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)
    landing_page_url = models.URLField(blank=True,
                                       null=True,
                                       default=None,
                                       help_text='All keyword articles must point to this page')
    is_deprecated = models.BooleanField(
        default=False,
        help_text=
        'Used when you want to stop using this cluster, all previous articles will be kept but no new articles will be assigned'
    )

    is_important = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=True)

    internal_description = models.TextField(default=None,
                                            null=True,
                                            blank=True,
                                            help_text='How will be this cluster be used in the SEO strategy')

    optimization_rating = models.FloatField(null=True,
                                            blank=True,
                                            default=None,
                                            help_text='Automatically filled (1 to 100)')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug
            cluster = KeywordCluster.objects.filter(slug=self.slug, academy=self.academy).first()
            if cluster is not None:
                raise Exception(f'Cluster with slug {self.slug} already exists on this academy')

        super().save(*args, **kwargs)


class AssetKeyword(models.Model):

    def __init__(self, *args, **kwargs):
        super(AssetKeyword, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text='E.g: en, es, it')

    cluster = models.ForeignKey(KeywordCluster,
                                on_delete=models.SET_NULL,
                                default=None,
                                blank=True,
                                null=True)

    expected_monthly_traffic = models.FloatField(null=True,
                                                 blank=True,
                                                 default=None,
                                                 help_text='You can get this info from Ahrefs or GKP')
    difficulty = models.FloatField(null=True, blank=True, default=None, help_text='From 1 to 100')
    is_important = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug
            keyword = AssetKeyword.objects.filter(slug=self.slug, academy=self.academy).first()
            if keyword is not None:
                raise Exception(f'Keyword with slug {self.slug} already exists on this academy')

        super().save(*args, **kwargs)


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
INTERMEDIATE = 'INTERMEDIATE'
HARD = 'HARD'
DIFFICULTY = (
    (HARD, 'Hard'),
    (INTERMEDIATE, 'Intermediate'),
    (EASY, 'Easy'),
    (BEGINNER, 'Beginner'),
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
    ('NEEDS_RESYNC', 'Needs Resync'),
)


class Asset(models.Model):

    def __init__(self, *args, **kwargs):
        super(Asset, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug
        self.__old_readme_raw = self.readme_raw

    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text=
        'Asset must be unique within the entire database because they could be published into 4geeks.com (shared among all academies)'
    )
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=2, blank=True, null=True, default=None, help_text='E.g: en, es, it')

    all_translations = models.ManyToManyField('self', blank=True)
    technologies = models.ManyToManyField(AssetTechnology, blank=True)

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
    readme_raw = models.TextField(null=True, blank=True, default=None)
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
    last_synch_at = models.DateTimeField(null=True, blank=True, default=None)
    # is_synched = models.BooleanField(default=True)

    test_status = models.CharField(max_length=20,
                                   choices=ASSET_SYNC_STATUS,
                                   default=None,
                                   null=True,
                                   blank=True,
                                   help_text='Internal state automatically set by the system based on test')
    published_at = models.DateTimeField(null=True, blank=True, default=None)
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

    seo_keywords = models.ManyToManyField(AssetKeyword,
                                          blank=True,
                                          help_text='Optimize for a max of two keywords per asset')

    optimization_rating = models.FloatField(null=True,
                                            blank=True,
                                            default=None,
                                            help_text='Automatically filled (1 to 100)')
    last_seo_scan_at = models.DateTimeField(null=True, blank=True, default=None)
    seo_json_status = models.JSONField(null=True, blank=True, default=None)

    # clean status refers to the cleaning of the readme file
    last_cleaning_at = models.DateTimeField(null=True, blank=True, default=None)
    cleaning_status_details = models.TextField(null=True, blank=True, default=None)
    cleaning_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default='PENDING',
        null=True,
        blank=True,
        help_text='Internal state automatically set by the system based on cleanup')

    delivery_instructions = models.TextField(null=True,
                                             default=None,
                                             blank=True,
                                             help_text='Tell students how to deliver this project')
    delivery_formats = models.CharField(
        max_length=255,
        default='url',
        help_text='Comma separated list of supported formats. Eg: url, image/png, application/pdf')
    delivery_regex_url = models.CharField(max_length=255,
                                          default=None,
                                          blank=True,
                                          null=True,
                                          help_text='Will only be used if "url" is the delivery format')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.slug}'

    def save(self, *args, **kwargs):

        slug_modified = False
        readme_modified = False

        if self.__old_readme_raw != self.readme_raw:
            readme_modified = True
            self.cleaning_status = 'PENDING'

        # only validate this on creation
        if self.pk is None or self.__old_slug != self.slug:
            slug_modified = True
            alias = AssetAlias.objects.filter(slug=self.slug).first()
            if alias is not None:
                raise Exception(
                    f'New slug {self.slug} for {self.__old_slug} is already taken by alias for asset {alias.asset.slug}'
                )

        super().save(*args, **kwargs)
        self.__old_slug = self.slug
        self.__old_readme_raw = self.readme_raw

        if slug_modified: asset_slug_modified.send(instance=self, sender=Asset)
        if readme_modified: asset_readme_modified.send(instance=self, sender=Asset)

    def get_readme(self, parse=None, remove_frontmatter=False):

        if self.readme is None:
            self.readme = self.readme_raw

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

        if self.readme_url is None and self.asset_type == 'LESSON':
            self.readme_url = self.url
            self.save()

        readme = {
            'clean': self.readme,
            'decoded': Asset.decode(self.readme),
            'raw': self.readme_raw,
            'decoded_raw': Asset.decode(self.readme_raw)
        }

        if parse:
            # external assets will have a default markdown readme generated internally
            extension = '.md'
            if self.readme_url and self.readme_url != '':
                u = urlparse(self.readme_url)
                extension = pathlib.Path(u[2]).suffix if not self.external else '.md'

            if extension in ['.md', '.mdx', '.txt']:
                readme = self.parse(readme, format='markdown', remove_frontmatter=remove_frontmatter)
            elif extension in ['.ipynb']:
                readme = self.parse(readme, format='notebook')
            else:
                AssetErrorLog(slug=AssetErrorLog.INVALID_README_URL,
                              path=self.slug,
                              asset_type=self.asset_type,
                              asset=self,
                              status_text='Invalid Readme URL').save()
        return readme

    def parse(self, readme, format='markdown', remove_frontmatter=False):
        if format == 'markdown':
            _data = frontmatter.loads(readme['decoded'])
            readme['frontmatter'] = _data.metadata
            readme['frontmatter']['format'] = format
            readme['decoded'] = _data.content
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

    @staticmethod
    def encode(content):
        if content is not None:
            return str(base64.b64encode(content.encode('utf-8')).decode('utf-8'))
        return None

    @staticmethod
    def decode(content):
        if content is not None:
            return base64.b64decode(content.encode('utf-8')).decode('utf-8')
        return None

    def set_readme(self, content):
        self.readme = Asset.encode(content)
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
    delivered = models.BooleanField(default=False)
    urgent = models.BooleanField(default=False)
    priority = models.SmallIntegerField(default=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    author = models.ForeignKey(User,
                               on_delete=models.SET_NULL,
                               default=None,
                               blank=True,
                               null=True,
                               help_text='Who wrote the comment or issue')
    owner = models.ForeignKey(User,
                              on_delete=models.SET_NULL,
                              default=None,
                              blank=True,
                              null=True,
                              related_name='assigned_comments',
                              help_text='In charge of resolving the comment or issue')

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
    INVALID_README_URL = 'invalid-readme-url'
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


class SEOReport(models.Model):

    report_type = models.CharField(max_length=40,
                                   help_text='Must be one of the services.seo.action script names')
    status = models.CharField(max_length=20,
                              choices=ASSET_SYNC_STATUS,
                              default='PENDING',
                              help_text='Internal state automatically set by the system')
    log = models.TextField(default=None, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    rating = models.FloatField(default=None,
                               null=True,
                               blank=True,
                               help_text='Automatically filled (1 to 100)')
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __init__(self, *args, **kwargs):
        super(SEOReport, self).__init__(*args, **kwargs)
        self.__log = []

    def fatal(self, msg):
        self.__log.append({'rating': -100, 'msg': msg})

    def good(self, rating, msg):
        self.__log.append({'rating': rating, 'msg': msg})

    def bad(self, rating, msg):
        self.__log.append({'rating': rating, 'msg': msg})

    def get_rating(self):
        total_rating = 100
        for entry in self.__log:
            total_rating += entry['rating']

        if total_rating < 0:
            return 0
        elif total_rating > 100:
            return 100
        else:
            return total_rating

    def get_log(self):
        return self.__log

    def to_json(self, rating, msg):
        return {'rating': self.get_rating(), 'log': self.__log}


class AssetImage(models.Model):
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=60)
    bucket_url = models.URLField(max_length=255)
    original_url = models.URLField(max_length=255)
    hash = models.CharField(max_length=64)

    assets = models.ManyToManyField(Asset, blank=True, related_name='images')

    last_download_at = models.DateTimeField(null=True, blank=True, default=None)
    download_details = models.TextField(null=True, blank=True, default=None)
    download_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default='PENDING',
        null=True,
        blank=True,
        help_text='Internal state automatically set by the system based on download')

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'{self.name} ({self.id})'
