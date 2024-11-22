import base64
import hashlib
import logging
import pathlib
import re
from urllib.parse import urlparse

import frontmatter
import markdown
from django.contrib.auth.models import AnonymousUser, User
from django.db import models
from django.db.models import Q
from django.template.loader import get_template
from django.utils import timezone
from slugify import slugify

from breathecode.admissions.models import Academy, SyllabusVersion
from breathecode.assessment.models import Assessment

from .signals import asset_readme_modified, asset_saved, asset_slug_modified, asset_status_updated, asset_title_modified

__all__ = ["AssetTechnology", "Asset", "AssetAlias"]
logger = logging.getLogger(__name__)

PUBLIC = "PUBLIC"
UNLISTED = "UNLISTED"
PRIVATE = "PRIVATE"
VISIBILITY = (
    (PUBLIC, "Public"),
    (UNLISTED, "Unlisted"),
    (PRIVATE, "Private"),
)
SORT_PRIORITY = (
    (1, 1),
    (2, 2),
    (3, 3),
)

LANG_MAP = {
    "en": "english",
    "es": "spanish",
    "it": "italian",
}


class SyllabusVersionProxy(SyllabusVersion):

    class Meta:
        proxy = True


class AssetTechnology(models.Model):
    slug = models.SlugField(max_length=200, unique=True, help_text="Technologies are unified within all 4geeks.com")
    title = models.CharField(max_length=200, blank=True)
    lang = models.CharField(
        max_length=2, blank=True, default=None, null=True, help_text="Leave blank if will be shown in all languages"
    )
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, default=None, blank=True, null=True)
    is_deprecated = models.BooleanField(
        default=False, help_text="If True, the technology will be programmatically deleted."
    )
    featured_asset = models.ForeignKey("Asset", on_delete=models.SET_NULL, default=None, blank=True, null=True)
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY,
        default=UNLISTED,
        help_text="If public, the front-end will generate a landing page. If unlisted, it won't have a landing page but will be shown in assets. If private, it won't be shown anywhere of the front-end.",
    )

    description = models.TextField(null=True, blank=True, default=None)
    icon_url = models.URLField(null=True, blank=True, default=None, help_text="Image icon to show on website")
    sort_priority = models.IntegerField(
        null=False,
        choices=SORT_PRIORITY,
        blank=False,
        default=3,
        help_text="Priority to sort technology (1, 2, or 3): One is more important and goes first than three.",
    )

    marketing_information = models.JSONField(
        null=True, blank=True, default=None, help_text="JSON structure for marketing information"
    )

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

    def clean(self):
        self.validate()

    def validate(self):
        if self.is_deprecated and self.parent is None:
            raise Exception("You cannot mark a technology as deprecated if it doesn't have a parent technology")


class AssetCategory(models.Model):

    def __init__(self, *args, **kwargs):
        super(AssetCategory, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text="E.g: en, es, it")
    description = models.TextField(null=True, blank=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    all_translations = models.ManyToManyField("self", blank=True)

    # Ideal for generating blog post thumbnails
    auto_generate_previews = models.BooleanField(default=False)
    preview_generation_url = models.URLField(
        null=True, blank=True, default=None, help_text="Will be POSTed to get preview image"
    )

    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug
            cat = AssetCategory.objects.filter(slug=self.slug, academy=self.academy).exclude(id=self.id).first()
            if cat is not None:
                raise Exception(f"Category with slug {self.slug} already exists on this academy")

        super().save(*args, **kwargs)


class KeywordCluster(models.Model):

    def __init__(self, *args, **kwargs):
        super(KeywordCluster, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text="E.g: en, es, it")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=VISIBILITY, default=PUBLIC)
    landing_page_url = models.URLField(
        blank=True, null=True, default=None, help_text="All keyword articles must point to this page"
    )
    is_deprecated = models.BooleanField(
        default=False,
        help_text="Used when you want to stop using this cluster, all previous articles will be kept but no new articles will be assigned",
    )

    is_important = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=True)

    internal_description = models.TextField(
        default=None, null=True, blank=True, help_text="How will be this cluster be used in the SEO strategy"
    )

    optimization_rating = models.FloatField(
        null=True, blank=True, default=None, help_text="Automatically filled (1 to 100)"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug
            cluster = KeywordCluster.objects.filter(slug=self.slug, academy=self.academy).first()
            if cluster is not None:
                raise Exception(f"Cluster with slug {self.slug} already exists on this academy")

        super().save(*args, **kwargs)


class AssetKeyword(models.Model):

    def __init__(self, *args, **kwargs):
        super(AssetKeyword, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug

    slug = models.SlugField(max_length=200)
    title = models.CharField(max_length=200)
    lang = models.CharField(max_length=2, help_text="E.g: en, es, it")

    cluster = models.ForeignKey(KeywordCluster, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    expected_monthly_traffic = models.FloatField(
        null=True, blank=True, default=None, help_text="You can get this info from Ahrefs or GKP"
    )
    difficulty = models.FloatField(null=True, blank=True, default=None, help_text="From 1 to 100")
    is_important = models.BooleanField(default=True)
    is_urgent = models.BooleanField(default=True)

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):

        if self.__old_slug != self.slug:
            # Prevent multiple keywords with same slug and make category mandatory
            keyword = AssetKeyword.objects.filter(slug=self.slug, academy=self.academy).first()
            if keyword is not None:
                raise Exception(f"Keyword with slug {self.slug} already exists on this academy")

        super().save(*args, **kwargs)


PROJECT = "PROJECT"
STARTER = "STARTER"
EXERCISE = "EXERCISE"
LESSON = "LESSON"
QUIZ = "QUIZ"
VIDEO = "VIDEO"
ARTICLE = "ARTICLE"
TYPE = (
    (PROJECT, "Project"),
    (STARTER, "Starter Template"),
    (EXERCISE, "Exercise"),
    (QUIZ, "Quiz"),
    (LESSON, "Lesson"),
    (VIDEO, "Video"),
    (ARTICLE, "Article"),
)

BEGINNER = "BEGINNER"
EASY = "EASY"
INTERMEDIATE = "INTERMEDIATE"
HARD = "HARD"
DIFFICULTY = (
    (HARD, "Hard"),
    (INTERMEDIATE, "Intermediate"),
    (EASY, "Easy"),
    (BEGINNER, "Beginner"),
)

NOT_STARTED = "NOT_STARTED"
PLANNING = "PLANNING"
WRITING = "WRITING"
DRAFT = "DRAFT"
OPTIMIZED = "OPTIMIZED"
PUBLISHED = "PUBLISHED"
ASSET_STATUS = (
    (NOT_STARTED, "Not Started"),
    (PLANNING, "Planning"),
    (WRITING, "Writing"),
    (DRAFT, "Draft"),
    (OPTIMIZED, "Optimized"),
    (PUBLISHED, "Published"),
)

ASSET_SYNC_STATUS = (
    ("PENDING", "Pending"),
    ("ERROR", "Error"),
    ("OK", "Ok"),
    ("WARNING", "Warning"),
    ("NEEDS_RESYNC", "Needs Resync"),
)


class Asset(models.Model):

    def __init__(self, *args, **kwargs):
        super(Asset, self).__init__(*args, **kwargs)
        self.__old_slug = self.slug
        self.__old_title = self.title
        self.__old_status = self.status
        self.__old_readme_raw = self.readme_raw

    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text="Asset must be unique within the entire database because they could be published into 4geeks.com (shared among all academies)",
        db_index=True,
    )
    title = models.CharField(max_length=200, blank=True, db_index=True)
    lang = models.CharField(
        max_length=2, blank=True, null=True, default=None, help_text="E.g: en, es, it", db_index=True
    )

    all_translations = models.ManyToManyField("self", blank=True)
    technologies = models.ManyToManyField(AssetTechnology, blank=True)

    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.SET_NULL,
        blank=False,
        null=True,
    )

    url = models.URLField(null=True, blank=True, default=None)
    solution_url = models.URLField(null=True, blank=True, default=None)
    preview = models.URLField(
        null=True, blank=True, default=None, help_text="This preview will be used when shared in social media"
    )
    preview_in_tutorial = models.URLField(
        null=True, blank=True, default=None, help_text="Used in 4geeks.com before the tutorial is about to start"
    )
    description = models.TextField(null=True, blank=True, default=None)
    requirements = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text="Brief for the copywriters, mainly used to describe what this lessons needs to be about",
    )

    learnpack_deploy_url = models.URLField(
        null=True,
        blank=True,
        default=None,
        help_text="Only applies to LearnPack tutorials that have been published in the LearnPack cloud",
    )

    template_url = models.URLField(
        null=True,
        blank=True,
        default=None,
        help_text="This template will be used to open the asset (only applied for projects)",
    )
    dependencies = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text="Automatically calculated based on the package.json, pipfile or alternatives. String like: python=3.10,node=16.0",
    )

    readme_url = models.URLField(
        null=True,
        blank=True,
        default=None,
        help_text="This will be used to synch only lessons from github. Projects, quizzes and exercises it will try README.md for english and README.lang.md for other langs",
    )
    intro_video_url = models.URLField(null=True, blank=True, default=None)
    solution_video_url = models.URLField(null=True, blank=True, default=None)
    readme = models.TextField(null=True, blank=True, default=None)
    readme_raw = models.TextField(null=True, blank=True, default=None)
    readme_updated_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    html = models.TextField(null=True, blank=True, default=None)

    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, null=True, default=None, blank=True)

    config = models.JSONField(null=True, blank=True, default=None)

    external = models.BooleanField(
        default=False,
        help_text="External assets will open in a new window, they are not built using breathecode or learnpack tecnology",
        db_index=True,
    )

    enable_table_of_content = models.BooleanField(
        default=True, help_text="If true, it shows a tabled on contents on top of the lesson"
    )
    interactive = models.BooleanField(default=False, db_index=True, help_text="If true, it means is learnpack enabled")
    with_solutions = models.BooleanField(default=False, db_index=True)
    with_video = models.BooleanField(default=False, db_index=True)
    graded = models.BooleanField(default=False, db_index=True)
    gitpod = models.BooleanField(
        default=False,
        help_text="If true, it means it can be opened on cloud provisioning vendors like Gitpod or Codespaces",
    )
    agent = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        default=None,
        help_text="If value is vscode, then we recommend to open this exercise/project in vscode and instructions will be different. If it is standalone, then you can open it directly from the terminal",
    )
    duration = models.IntegerField(null=True, blank=True, default=None, help_text="In hours")

    difficulty = models.CharField(max_length=20, choices=DIFFICULTY, default=None, null=True, blank=True)

    # NOT RELATED TO SEO, VISIBILITY IS INTERNAL, other academies won't see it!!!!
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY,
        default=PUBLIC,
        help_text="This is an internal property. It won't be shown internally to other academies unless is public",
        db_index=True,
    )
    asset_type = models.CharField(max_length=20, choices=TYPE, db_index=True)

    superseded_by = models.OneToOneField(
        "Asset",
        related_name="previous_version",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        help_text="The newer version of the article (null if it is the latest version). This is used for technology deprecation, for example, a new article to explain the new version of react router",
    )

    status = models.CharField(
        max_length=20,
        choices=ASSET_STATUS,
        default=NOT_STARTED,
        help_text="It won't be shown on the website until the status is published",
        db_index=True,
    )

    is_auto_subscribed = models.BooleanField(
        default=True,
        help_text="If auto subscribed, the system will attempt to listen to push event and update the asset meta based on github",
    )
    sync_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default=None,
        null=True,
        blank=True,
        help_text="Internal state automatically set by the system based on sync",
        db_index=True,
    )
    last_synch_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    github_commit_hash = models.CharField(max_length=100, null=True, blank=True, default=None, db_index=True)

    test_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default=None,
        null=True,
        blank=True,
        help_text="Internal state automatically set by the system based on test",
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    last_test_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    status_text = models.TextField(
        null=True, default=None, blank=True, help_text="Used by the sych status to provide feedback"
    )

    authors_username = models.CharField(
        max_length=80,
        null=True,
        default=None,
        blank=True,
        help_text="Github usernames separated by comma",
        db_index=True,
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="Connection with the assessment breathecode app",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="Who wrote the lesson, not necessarily the owner",
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="owned_lessons",
        default=None,
        blank=True,
        null=True,
        help_text="The owner has the github premissions to update the lesson",
    )

    is_seo_tracked = models.BooleanField(default=True, db_index=True)
    seo_keywords = models.ManyToManyField(
        AssetKeyword, blank=True, help_text="Optimize for a max of two keywords per asset"
    )

    optimization_rating = models.FloatField(
        null=True, blank=True, default=None, help_text="Automatically filled (1 to 100)"
    )
    last_seo_scan_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    seo_json_status = models.JSONField(null=True, blank=True, default=None)

    # clean status refers to the cleaning of the readme file

    last_cleaning_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    cleaning_status_details = models.TextField(null=True, blank=True, default=None)
    cleaning_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default="PENDING",
        null=True,
        blank=True,
        help_text="Internal state automatically set by the system based on cleanup",
        db_index=True,
    )

    delivery_instructions = models.TextField(
        null=True, default=None, blank=True, help_text="Tell students how to deliver this project"
    )
    delivery_formats = models.CharField(
        max_length=255,
        default="url",
        help_text="Comma separated list of supported formats. Eg: url, image/png, application/pdf",
    )
    delivery_regex_url = models.CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
        help_text='Will only be used if "url" is the delivery format',
    )

    assets_related = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        help_text="Related assets used to get prepared before going through this asset.",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.slug}"

    def build_ai_context(self):
        lang = self.lang or self.category.lang
        lang_name = LANG_MAP.get(lang, lang)

        context = f"This {self.asset_type} about {self.title} is written in {lang_name}. "

        translations = ", ".join([x.title for x in self.all_translations.all()])
        if translations:
            context = context[:-2]
            context += f", and it has the following translations: {translations}. "

        if self.solution_url:
            context = context[:-2]
            context += f", and it has a solution code this link is: {self.solution_url}. "

        if self.solution_video_url:
            context = context[:-2]
            context += f", and it has a video solution this link is {self.solution_video_url}. "

        context += f"It's category related is (what type of skills the student will get) {self.category.title}. "

        technologies = ", ".join([x.title for x in self.technologies.filter(Q(lang=lang) | Q(lang=None))])
        if technologies:
            context += f"This asset is about the following technologies: {technologies}. "

        if self.external:
            context += "This asset is external, which means it opens outside 4geeks. "

        if self.interactive:
            context += (
                "This asset opens on LearnPack so it has a step-by-step of the exercises that you should follow. "
            )

        if self.gitpod:
            context += (
                f"This {self.asset_type} can be opened both locally or with click and code (This "
                "way you don't have to install anything and it will open automatically on gitpod or github codespaces). "
            )

        if self.interactive == True and self.with_video == True:
            context += f"This {self.asset_type} has videos on each step. "

        if self.interactive == True and self.with_solutions == True:
            context += f"This {self.asset_type} has a code solution on each step. "

        if self.duration:
            context += f"This {self.asset_type} will last {self.duration} hours. "

        if self.difficulty:
            context += f"Its difficulty is considered as {self.difficulty}. "

        if self.superseded_by and self.superseded_by.title != self.title:
            context += f"This {self.asset_type} has a previous version which is: {self.superseded_by.title}. "

        if self.asset_type == "PROJECT" and not self.delivery_instructions:
            context += "This project should be delivered by sending a github repository URL. "

        if self.asset_type == "PROJECT" and self.delivery_instructions and self.delivery_formats:
            context += (
                f"This project should be delivered by adding a file of one of these types: {self.delivery_formats}. "
            )

        if self.asset_type == "PROJECT" and self.delivery_regex_url:
            context += (
                f"This project should be delivered with a URL that follows this format: {self.delivery_regex_url}. "
            )

        assets_related = ", ".join([x.slug for x in self.assets_related.all()])
        if assets_related:
            context += (
                f"In case you still need to learn more about the basics of this {self.asset_type}, "
                "you can check these lessons, and exercises, "
                f"and related projects to get ready for this content: {assets_related}. "
            )

        if self.html:
            context += "The markdown file with "

            if self.asset_type == "PROJECT":
                context += "the instructions"
            else:
                context += "the content"

            context += f" of this {self.asset_type} is the following: {self.html}."

        return context

    def save(self, *args, **kwargs):

        slug_modified = False
        title_modified = False
        readme_modified = False
        status_modified = False

        if self.__old_readme_raw != self.readme_raw:
            readme_modified = True
            self.readme_updated_at = timezone.now()
            self.cleaning_status = "PENDING"

        if self.__old_title != self.title:
            title_modified = True

        if self.__old_status != self.status:
            status_modified = True

        # only validate this on creation
        if self.pk is None or self.__old_slug != self.slug:
            slug_modified = True
            alias = AssetAlias.objects.filter(slug=self.slug).first()
            if alias is not None:
                raise Exception(
                    f"New slug {self.slug} for {self.__old_slug} is already taken by alias for asset {alias.asset.slug}"
                )
        self.full_clean()

        super().save(*args, **kwargs)
        self.__old_slug = self.slug
        self.__old_readme_raw = self.readme_raw
        self.__old_status = self.status

        if slug_modified:
            asset_slug_modified.send_robust(instance=self, sender=Asset)
        if readme_modified:
            asset_readme_modified.send_robust(instance=self, sender=Asset)
        if title_modified:
            asset_title_modified.send_robust(instance=self, sender=Asset)
        if status_modified:
            asset_status_updated.send_robust(instance=self, sender=Asset)

        asset_saved.delay(instance=self, sender=Asset)

    def get_preview_generation_url(self):

        if self.category is not None:
            return self.category.preview_generation_url

        return None

    def get_repo_meta(self):
        # def get_url_info(url: str):
        url = self.readme_url
        result = re.search(r"blob\/([\w\-]+)", url)
        branch_name = None
        if result is not None:
            branch_name = result.group(1)

        result = re.search(r"https?:\/\/github\.com\/([\w\-]+)\/([\w\-]+)\/?", url)
        if result is None:
            raise Exception("Invalid URL when looking organization: " + url)

        org_name = result.group(1)
        repo_name = result.group(2)

        return org_name, repo_name, branch_name

    def get_readme(self, parse=None, remove_frontmatter=False):

        if self.readme is None:
            self.readme = self.readme_raw

        if self.readme is None or self.readme == "":
            if self.asset_type != "QUIZ":
                AssetErrorLog(
                    slug=AssetErrorLog.EMPTY_README,
                    path=self.slug,
                    asset_type=self.asset_type,
                    asset=self,
                    status_text="Readme file was not found",
                ).save()
            self.set_readme(
                get_template("empty.md").render(
                    {
                        "title": self.title,
                        "lang": self.lang,
                        "asset_type": self.asset_type,
                    }
                )
            )

        if self.readme_url is None and self.asset_type == "LESSON":
            self.readme_url = self.url
            self.save()

        readme = {
            "clean": self.readme,
            "decoded": Asset.decode(self.readme),
            "raw": self.readme_raw,
            "decoded_raw": Asset.decode(self.readme_raw),
        }

        if parse:
            # external assets will have a default markdown readme generated internally
            extension = ".md"
            if self.readme_url and self.readme_url != "":
                u = urlparse(self.readme_url)
                extension = pathlib.Path(u[2]).suffix if not self.external else ".md"

            if extension in [".md", ".mdx", ".txt"]:
                readme = self.parse(readme, format="markdown", remove_frontmatter=remove_frontmatter)
            elif extension in [".ipynb"]:
                readme = self.parse(readme, format="notebook")
            else:
                AssetErrorLog(
                    slug=AssetErrorLog.INVALID_README_URL,
                    path=self.slug,
                    asset_type=self.asset_type,
                    asset=self,
                    status_text="Invalid Readme URL",
                ).save()
        return readme

    def parse(self, readme, format="markdown", remove_frontmatter=False):
        if format == "markdown":
            _data = frontmatter.loads(readme["decoded"])
            readme["frontmatter"] = _data.metadata
            readme["frontmatter"]["format"] = format
            readme["decoded"] = _data.content
            readme["html"] = markdown.markdown(_data.content, extensions=["markdown.extensions.fenced_code"])
        if format == "notebook":
            import nbformat
            from nbconvert import HTMLExporter

            notebook = nbformat.reads(readme["decoded"], as_version=4)
            # Instantiate the exporter. We use the `classic` template for now; we'll get into more details
            # later about how to customize the exporter further. You can use 'basic'
            html_exporter = HTMLExporter(template_name="basic")
            # Process the notebook we loaded earlier
            body, resources = html_exporter.from_notebook_node(notebook)
            readme["frontmatter"] = resources
            readme["frontmatter"]["format"] = format
            readme["html"] = body
        return readme

    def get_thumbnail_name(self):

        slug1 = self.category.slug if self.category is not None else "default"
        slug2 = self.slug

        if self.academy is None:
            raise Exception("Asset needs to belong to an academy to generate its thumbnail")

        return f"{self.academy.slug}-{slug1}-{slug2}.png"

    @staticmethod
    def encode(content):
        if content is not None:
            return str(base64.b64encode(content.encode("utf-8")).decode("utf-8"))
        return None

    @staticmethod
    def decode(content):
        if content is not None:
            return base64.b64decode(content.encode("utf-8")).decode("utf-8")
        return None

    def set_readme(self, content):
        self.readme = Asset.encode(content)
        return self

    def log_error(self, error_slug, status_text=None):
        error = AssetErrorLog(
            slug=error_slug, asset=self, asset_type=self.asset_type, status_text=status_text, path=self.slug
        )
        error.save()
        return error

    def generate_quiz_json(self):

        if not self.assessment:
            return None

        config = self.assessment.to_json()
        config["info"]["description"] = self.description
        config["lang"] = self.lang
        config["technologies"] = [t.slug for t in self.technologies.all()]

        return config

    def get_tasks(self):

        if self.readme is None:
            return []

        regex = r"\-\s\[(?P<status>[\sxX-])\]\s(?P<label>.+)"
        findings = list(re.finditer(regex, self.get_readme()["decoded"]))
        tasks = []
        while len(findings) > 0:
            task_find = findings.pop(0)
            task = task_find.groupdict()
            task["id"] = hashlib.md5(task["label"].encode("utf-8")).hexdigest()
            task["status"] = "DONE" if "status" in task and task["status"].strip().lower() == "x" else "PENDING"

            tasks.append(task)
        return tasks

    @staticmethod
    def get_by_slug(asset_slug, request=None, asset_type=None):
        is_alias = True
        user = None
        if request is not None and not isinstance(request.user, AnonymousUser):
            user = request.user

        alias = AssetAlias.objects.filter(Q(slug=asset_slug) | Q(asset__slug=asset_slug)).first()
        if not alias:
            alias = Asset.objects.filter(slug=asset_slug).first()
            is_alias = False

        if alias is None:
            AssetErrorLog(slug=AssetErrorLog.SLUG_NOT_FOUND, path=asset_slug, asset_type=asset_type, user=user).save()
            return None
        elif asset_type is not None and alias.asset.asset_type.lower() == asset_type.lower():
            AssetErrorLog(
                slug=AssetErrorLog.DIFFERENT_TYPE, path=asset_slug, asset=alias.asset, asset_type=asset_type, user=user
            ).save()

        elif is_alias:
            return alias.asset

        else:
            return alias

    @staticmethod
    def get_by_github_url(github_url):
        parsed_url = urlparse(github_url)
        if parsed_url.netloc != "github.com":
            raise ValueError("Invalid GitHub URL")

        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError("Invalid GitHub URL")

        org_name, repo_name = path_parts[:2]
        asset = Asset.objects.filter(readme_url__icontains=f"github.com/{org_name}/{repo_name}").first()
        return asset


PENDING = "PENDING"
PROCESSING = "PROCESSING"
DONE = "DONE"
ERROR = "ERROR"
ASSETCONTEXT_STATUS = (
    (PENDING, "PENDING"),
    (PROCESSING, "PROCESSING"),
    (DONE, "DONE"),
    (ERROR, "ERROR"),
)


class AssetContext(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    ai_context = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ASSETCONTEXT_STATUS,
        default=PENDING,
        help_text="If pending, it means it hasn't been generated yet, processing means that is being generated at this moment, done means it has been generated",
        db_index=True,
    )
    status_text = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text="Status details, it may be set automatically if enough error information",
    )


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
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, default=None, blank=True, null=True, help_text="Who wrote the comment or issue"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="assigned_comments",
        help_text="In charge of resolving the comment or issue",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return "AssetComment " + str(self.id)


ERROR = "ERROR"
FIXED = "FIXED"
IGNORED = "IGNORED"
ERROR_STATUS = (
    (ERROR, "Error"),
    (FIXED, "Fixed"),
    (IGNORED, "Ignored"),
)


class AssetErrorLog(models.Model):
    SLUG_NOT_FOUND = "slug-not-found"
    DIFFERENT_TYPE = "different-type"
    EMPTY_README = "empty-readme"
    EMPTY_HTML = "empty-html"
    INVALID_URL = "invalid-url"
    INVALID_README_URL = "invalid-readme-url"
    README_SYNTAX = "readme-syntax-error"

    asset_type = models.CharField(max_length=20, choices=TYPE, default=None, null=True, blank=True)
    slug = models.SlugField(max_length=200)
    status = models.CharField(max_length=20, choices=ERROR_STATUS, default=ERROR)
    path = models.CharField(max_length=200)
    status_text = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text="Status details, it may be set automatically if enough error information",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        help_text="The user how asked for the asset and got the error",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        help_text='Assign an asset to this error and you will be able to create an alias for it from the django admin bulk actions "create alias"',
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"Error {self.status} with {self.slug}"


class SEOReport(models.Model):

    def __init__(self, *args, **kwargs):
        super(SEOReport, self).__init__(*args, **kwargs)
        self.__shared_state = {}
        self.__log = []

    report_type = models.CharField(max_length=40, help_text="Must be one of the services.seo.action script names")
    status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default="PENDING",
        help_text="Internal state automatically set by the system",
    )
    log = models.JSONField(default=None, null=True, blank=True)
    how_to_fix = models.TextField(default=None, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    rating = models.FloatField(default=None, null=True, blank=True, help_text="Automatically filled (1 to 100)")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def fatal(self, msg):
        self.__log.append({"rating": -100, "msg": msg})

    def good(self, rating, msg):
        self.__log.append({"rating": rating, "msg": msg})

    def bad(self, rating, msg):
        self.__log.append({"rating": rating, "msg": msg})

    # this data will be shared among all reports as they are
    # being calculated in real time
    def get_state(self):
        return self.__shared_data

    def set_state(self, key, value):
        attrs = ["words"]
        if key in attrs:
            self.__shared_state[key]: value
        else:
            raise Exception(f"Trying to set invalid property {key} on SEO report shared state")

    def get_rating(self):
        total_rating = 100
        for entry in self.__log:
            total_rating += entry["rating"]

        if total_rating < 0:
            return 0
        elif total_rating > 100:
            return 100
        else:
            return total_rating

    def get_log(self):
        return self.__log

    def to_json(self, rating, msg):
        return {"rating": self.get_rating(), "log": self.__log}


class AssetImage(models.Model):
    name = models.CharField(max_length=150)
    mime = models.CharField(max_length=60)
    bucket_url = models.URLField(max_length=255)
    original_url = models.URLField(max_length=255)
    hash = models.CharField(max_length=64)

    assets = models.ManyToManyField(Asset, blank=True, related_name="images")

    last_download_at = models.DateTimeField(null=True, blank=True, default=None)
    download_details = models.TextField(null=True, blank=True, default=None)
    download_status = models.CharField(
        max_length=20,
        choices=ASSET_SYNC_STATUS,
        default="PENDING",
        null=True,
        blank=True,
        help_text="Internal state automatically set by the system based on download",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class CredentialsOriginality(models.Model):

    token = models.CharField(max_length=255)
    balance = models.FloatField(default=0)  # balance
    usage = models.JSONField(default=dict)
    last_call_at = models.DateTimeField(default=None, null=True, blank=True)

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


ASSET_ORIGINALITY_STATUS = (
    ("PENDING", "Pending"),
    ("ERROR", "Error"),
    ("COMPLETED", "Completed"),
    ("WARNING", "Warning"),
)


class OriginalityScan(models.Model):

    success = models.BooleanField(null=True, default=None, blank=True)
    score_original = models.FloatField(null=True, default=None, blank=True)
    score_ai = models.FloatField(null=True, default=None, blank=True)
    credits_used = models.IntegerField(default=0)
    content = models.TextField()

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20, choices=ASSET_ORIGINALITY_STATUS, default="PENDING", help_text="Scan for originality"
    )
    status_text = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


VARIABLE_TYPE = (
    ("MARKDOWN", "Markdown"),
    ("PYTHON_CODE", "Python"),
    ("FETCH_JSON", "Fetch json from url"),
    ("FETCH_TEXT", "Fetch text from url"),
)

CONTENT_VAR_STATUS = (
    ("PENDING", "Pending"),
    ("ERROR", "Error"),
    ("COMPLETED", "Completed"),
)


class ContentVariable(models.Model):

    key = models.CharField(max_length=100)
    value = models.TextField()
    default_value = models.TextField(
        help_text="If the variable type is fetch or code and the processing fails, the default value will be used"
    )

    lang = models.CharField(
        max_length=2, blank=True, default=None, null=True, help_text="Leave blank if will be shown in all languages"
    )

    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    var_type = models.CharField(
        max_length=20,
        choices=VARIABLE_TYPE,
        default="MARKDOWN",
        help_text="Code vars accept python code, Fetch vars accept HTTP GET",
    )

    status = models.CharField(
        max_length=20,
        choices=CONTENT_VAR_STATUS,
        default="PENDING",
        help_text="Code vars accept python code, Fetch vars accept HTTP GET",
    )

    status_text = models.TextField(
        null=True,
        default=None,
        blank=True,
        help_text="If the var is code or fetch here will be the error processing info",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
