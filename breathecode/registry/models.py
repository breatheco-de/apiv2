import base64, frontmatter, markdown
from django.db import models
from django.contrib.auth.models import User
from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event

__all__ = ['AssetTranslation', 'AssetTechnology', 'Asset', 'AssetAlias']


class AssetTranslation(models.Model):
    slug = models.SlugField(max_length=2, primary_key=True)
    title = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title


class AssetTechnology(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    title = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title


PUBLIC = 'PUBLIC'
UNLISTED = 'UNLISTED'
PRIVATE = 'PRIVATE'
VISIBILITY = (
    (PUBLIC, 'Public'),
    (UNLISTED, 'Unlisted'),
    (PRIVATE, 'Private'),
)

PROJECT = 'PROJECT'
EXERCISE = 'EXERCISE'
LESSON = 'LESSON'
QUIZ = 'QUIZ'
VIDEO = 'VIDEO'
TYPE = (
    (PROJECT, 'Project'),
    (EXERCISE, 'Exercise'),
    (QUIZ, 'Quiz'),
    (LESSON, 'Lesson'),
    (VIDEO, 'Video'),
)

BEGINNER = 'BEGINNER'
EASY = 'EASY'
DIFFICULTY = (
    (BEGINNER, 'Beginner'),
    (EASY, 'Easy'),
)

DRAFT = 'DRAFT'
UNNASIGNED = 'UNNASIGNED'
OK = 'OK'
ASSET_STATUS = (
    (UNNASIGNED, 'Unnasigned'),
    (DRAFT, 'Draft'),
    (OK, 'Ok'),
)

ASSET_SYNC_STATUS = (
    ('PENDING', 'Pending'),
    ('ERROR', 'Error'),
    ('OK', 'Ok'),
    ('WARNING', 'Warning'),
)


class Asset(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(max_length=50, blank=True, null=True, default=None)

    translations = models.ManyToManyField(AssetTranslation)
    technologies = models.ManyToManyField(AssetTechnology)

    url = models.URLField()
    solution_url = models.URLField(null=True, blank=True, default=None)
    preview = models.URLField(null=True, blank=True, default=None)
    description = models.TextField(null=True, blank=True, default=None)
    readme_url = models.URLField(null=True,
                                 blank=True,
                                 default=None,
                                 help_text='This will be used to synch from github')
    intro_video_url = models.URLField(null=True, blank=True, default=None)
    solution_video_url = models.URLField(null=True, blank=True, default=None)
    readme = models.TextField(null=True, blank=True, default=None)

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
                              default=DRAFT,
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
        return f'{self.title} ({self.slug})'

    def save(self, *args, **kwargs):

        # only validate this on creation
        if self.created_at is None:
            alias = AssetAlias.objects.filter(slug=self.slug).first()
            if alias is not None:
                raise Exception('Slug is already taken by alias')
            super().save(*args, **kwargs)
            AssetAlias.objects.create(slug=self.slug, asset=self)

        else:
            super().save(*args, **kwargs)

    def get_readme(self, parse=False):
        readme = {
            'raw': self.readme,
            'decoded': base64.b64decode(self.readme.encode('utf-8')).decode('utf-8')
        }
        if parse:
            _data = frontmatter.loads(readme['decoded'])
            readme['frontmatter'] = _data.metadata
            readme['html'] = markdown.markdown(_data.content, extensions=['markdown.extensions.fenced_code'])
        return readme

    def set_readme(self, content):
        self.readme = str(base64.b64encode(content.encode('utf-8')).decode('utf-8'))


class AssetAlias(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.slug
