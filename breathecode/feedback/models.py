import datetime
import json
import uuid as uuid_lib

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

import breathecode.feedback.signals as signals
from breathecode.admissions.models import Academy, Cohort, CohortUser
from breathecode.authenticate.models import Token
from breathecode.events.models import Event, LiveClass
from breathecode.feedback.utils import strings
from breathecode.mentorship.models import MentorshipSession
from breathecode.registry.models import Asset

__all__ = [
    "UserProxy",
    "CohortUserProxy",
    "CohortProxy",
    "Survey",
    "Answer",
    "SurveyTemplate",
    "FeedbackTag",
    "SurveyQuestionTemplate",
    "SurveyStudy",
    "SurveyConfiguration",
    "SurveyResponse",
]


class UserProxy(User):

    class Meta:
        proxy = True


class CohortUserProxy(CohortUser):

    class Meta:
        proxy = True


class CohortProxy(Cohort):

    class Meta:
        proxy = True


PENDING = "PENDING"
SENT = "SENT"
PARTIAL = "PARTIAL"
FATAL = "FATAL"
SURVEY_STATUS = (
    (SENT, "Sent"),
    (PENDING, "Pending"),
    (PARTIAL, "Partial"),
    (FATAL, "Fatal"),
)


class FeedbackTag(models.Model):
    """
    Tags for categorizing and organizing feedback (answers, reviews, surveys).
    Tags can be academy-specific or shared across all academies.
    """

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, help_text="Description of what this tag represents")
    priority = models.IntegerField(
        default=100, help_text="Lower numbers appear first. Use for sorting tags by importance"
    )

    academy = models.ForeignKey(
        Academy,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="If null, tag is available to all academies (when is_private=False)",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="If False and academy is null, tag is shared among all academies. If True, tag is only visible to its academy",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        visibility = "private" if self.is_private else "public"
        owner = f"{self.academy.name}" if self.academy else "shared"
        return f"{self.title} ({owner}, {visibility})"

    class Meta:
        ordering = ["priority", "title"]
        verbose_name = "Feedback Tag"
        verbose_name_plural = "Feedback Tags"


class Survey(models.Model):
    """
    Multiple questions/answers for one single person, surveys can only be send to entire cohorts and they will ask all the possible questions involved in a cohort
    1. How is your teacher?
    2. How is the academy?
    3. How is the blabla..
    """

    lang = models.CharField(max_length=3, blank=True, default="en")
    title = models.CharField(
        max_length=200, blank=True, null=True, help_text="Automatically set from the questions inside"
    )
    template_slug = models.CharField(
        max_length=100, blank=True, null=True, help_text="Slug of the template that was used to create this survey"
    )

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    is_customized = models.BooleanField(
        default=False, help_text="Customized surveys are not based on the default questions for a cohort"
    )

    max_assistants_to_ask = models.IntegerField(default=2, blank=True, null=True)
    max_teachers_to_ask = models.IntegerField(default=1, blank=True, null=True)

    scores = models.JSONField(default=None, blank=True, null=True)
    response_rate = models.FloatField(default=None, blank=True, null=True)

    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=PENDING)
    status_json = models.JSONField(default=None, null=True, blank=True)

    duration = models.DurationField(
        default=datetime.timedelta(hours=24), help_text="No one will be able to answer after this period of time"
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return "Survey for " + self.cohort.name


PENDING = "PENDING"
SENT = "SENT"
ANSWERED = "ANSWERED"
OPENED = "OPENED"
EXPIRED = "EXPIRED"
SURVEY_STATUS = (
    (PENDING, "Pending"),
    (SENT, "Sent"),
    (ANSWERED, "Answered"),
    (OPENED, "Opened"),
    (EXPIRED, "Expired"),
)


class Answer(models.Model):

    def __init__(self, *args, **kwargs):
        super(Answer, self).__init__(*args, **kwargs)
        self.__old_status = self.status

    title = models.CharField(max_length=200, blank=True)
    lowest = models.CharField(max_length=50, default="not likely")
    highest = models.CharField(max_length=50, default="very likely")
    lang = models.CharField(max_length=3, blank=True, default="en")

    question_by_slug = models.CharField(
        max_length=100, default=None, blank=True, null=True, help_text="Ideal to create new standarized questions"
    )
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    live_class = models.ForeignKey(LiveClass, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    mentorship_session = models.ForeignKey(
        MentorshipSession, on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    mentor = models.ForeignKey(
        User, related_name="mentor_set", on_delete=models.SET_NULL, default=None, blank=True, null=True
    )
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    academy = models.ForeignKey(Academy, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    token = models.OneToOneField(Token, on_delete=models.SET_NULL, default=None, blank=True, null=True)

    # Optional categorization fields
    syllabus = models.ForeignKey(
        "admissions.Syllabus",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="Optional syllabus association for filtering and reporting",
    )
    course_slug = models.CharField(
        max_length=150,
        default=None,
        blank=True,
        null=True,
        help_text="Optional course slug from marketing.Course model for filtering and reporting",
    )
    tags = models.ManyToManyField(
        FeedbackTag, blank=True, related_name="answers", help_text="Tags for categorizing this answer"
    )

    score = models.IntegerField(default=None, blank=True, null=True)
    comment = models.TextField(max_length=1000, default=None, blank=True, null=True)

    survey = models.ForeignKey(
        Survey,
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="You can group one or more answers in one survey, the survey does not belong to any student in particular but answers belong to the student that answered",
    )

    status = models.CharField(max_length=15, choices=SURVEY_STATUS, default=PENDING)

    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True)

    opened_at = models.DateTimeField(default=None, blank=True, null=True)
    sent_at = models.DateTimeField(default=None, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)  # Call the "real" save() method.

        if self.__old_status != self.status and self.status == "ANSWERED":

            # signal the updated answer
            signals.survey_answered.send_robust(instance=self, sender=Answer)

        self.__old_status = self.status


class ReviewPlatform(models.Model):
    """
    Websites like KareerKarma, Switchup, Coursereport, etc.
    """

    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    website = models.URLField()
    review_signup = models.URLField(blank=True, null=True, default=None, help_text="Give URL to create a new review")
    contact_email = models.EmailField()
    contact_name = models.EmailField(blank=True, null=True, default=None)
    contact_phone = models.CharField(max_length=17, blank=True, null=True, default=None)

    def __str__(self):
        return f"{self.slug}"


PENDING = "PENDING"
REQUESTED = "REQUESTED"
DONE = "DONE"
IGNORE = "IGNORE"
REVIEW_STATUS = (
    (PENDING, "Pending"),
    (REQUESTED, "Requested"),
    (DONE, "Done"),
    (IGNORE, "Ignore"),
)


class Review(models.Model):

    nps_previous_rating = models.FloatField(
        blank=True, null=True, default=None, help_text="Automatically calculated based on NPS survey responses"
    )
    total_rating = models.FloatField(blank=True, null=True, default=None)
    public_url = models.URLField(blank=True, null=True, default=None)

    status = models.CharField(
        max_length=9, choices=REVIEW_STATUS, default=PENDING, help_text="Deleted reviews hav status=Ignore"
    )
    status_text = models.CharField(max_length=255, default=None, null=True, blank=True)
    comments = models.TextField(
        default=None, null=True, blank=True, help_text="Student comments when leaving the review"
    )

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    platform = models.ForeignKey(ReviewPlatform, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    lang = models.CharField(max_length=3, blank=True, null=True)
    
    # Optional categorization fields
    syllabus = models.ForeignKey(
        "admissions.Syllabus",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        help_text="Optional syllabus association for filtering and reporting",
    )
    course_slug = models.CharField(
        max_length=150,
        default=None,
        blank=True,
        null=True,
        help_text="Optional course slug from marketing.Course model for filtering and reporting",
    )
    tags = models.ManyToManyField(
        FeedbackTag, blank=True, related_name="reviews", help_text="Tags for categorizing this review"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        cohort = "no specific cohort"
        if self.cohort is not None:
            cohort = self.cohort.slug
        return f"{self.author.first_name} {self.author.last_name} for {cohort}"


def validate_question_structure(value):
    """Validate that the JSON question structure contains all required fields"""
    if value is None:
        return

    required_keys = ["title", "highest", "lowest", "survey_subject"]

    if not isinstance(value, dict):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            raise ValidationError("Value must be a dictionary or a valid JSON string")

    missing_keys = [key for key in required_keys if key not in value]
    if missing_keys:
        raise ValidationError(f'Missing required keys: {", ".join(missing_keys)}')


class SurveyTemplate(models.Model):
    """Template used to create surveys with predefined questions"""

    slug = models.SlugField(max_length=100, unique=True)
    lang = models.CharField(max_length=2, help_text="Two-letter language code")
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    is_shared = models.BooleanField(default=False, help_text="If true, other academies can use this template")

    original = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="translations")

    # JSON fields for different question types
    when_asking_event = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about an event",
        default=dict(
            title=strings["en"]["event"]["title"],
            highest=strings["en"]["event"]["highest"],
            lowest=strings["en"]["event"]["lowest"],
            survey_subject=strings["en"]["event"]["survey_subject"],
        ),
    )
    when_asking_mentor = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about a mentor",
        default=dict(
            title=strings["en"]["mentor"]["title"],
            highest=strings["en"]["mentor"]["highest"],
            lowest=strings["en"]["mentor"]["lowest"],
            survey_subject=strings["en"]["mentor"]["survey_subject"],
        ),
    )
    when_asking_cohort = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about a cohort",
        default=dict(
            title=strings["en"]["cohort"]["title"],
            highest=strings["en"]["cohort"]["highest"],
            lowest=strings["en"]["cohort"]["lowest"],
            survey_subject=strings["en"]["cohort"]["survey_subject"],
        ),
    )
    when_asking_academy = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about the academy",
        default=dict(
            title=strings["en"]["academy"]["title"],
            highest=strings["en"]["academy"]["highest"],
            lowest=strings["en"]["academy"]["lowest"],
            survey_subject=strings["en"]["academy"]["survey_subject"],
        ),
    )
    when_asking_mentorshipsession = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about a mentorship session",
        default=dict(
            title=strings["en"]["mentorship_session"]["title"],
            highest=strings["en"]["mentorship_session"]["highest"],
            lowest=strings["en"]["mentorship_session"]["lowest"],
            survey_subject=strings["en"]["mentorship_session"]["survey_subject"],
        ),
    )
    when_asking_platform = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about the 4Geeks.com platform",
        default=dict(
            title=strings["en"]["platform"]["title"],
            highest=strings["en"]["platform"]["highest"],
            lowest=strings["en"]["platform"]["lowest"],
            survey_subject=strings["en"]["platform"]["survey_subject"],
        ),
    )
    when_asking_liveclass_mentor = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about a live class mentor",
        default=dict(
            title=strings["en"]["liveclass_mentor"]["title"],
            highest=strings["en"]["liveclass_mentor"]["highest"],
            lowest=strings["en"]["liveclass_mentor"]["lowest"],
            survey_subject=strings["en"]["liveclass_mentor"]["survey_subject"],
        ),
    )
    when_asking_mentor_communication = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about mentor communication during class",
        default=dict(
            title=strings["en"]["mentor_communication"]["title"],
            highest=strings["en"]["mentor_communication"]["highest"],
            lowest=strings["en"]["mentor_communication"]["lowest"],
            survey_subject=strings["en"]["mentor_communication"]["survey_subject"],
        ),
    )
    when_asking_mentor_participation = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about class how the mentor answers and encoursges participation",
        default=dict(
            title=strings["en"]["mentor_participation"]["title"],
            highest=strings["en"]["mentor_participation"]["highest"],
            lowest=strings["en"]["mentor_participation"]["lowest"],
            survey_subject=strings["en"]["mentor_participation"]["survey_subject"],
        ),
    )
    additional_questions = models.JSONField(
        null=True, blank=True, help_text="Additional custom questions in the same structure"
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        """Validate additional_questions if present and language/original relationships"""
        if self.additional_questions:
            if not isinstance(self.additional_questions, dict):
                raise ValidationError({"additional_questions": "Must be a dictionary"})

            for key, value in self.additional_questions.items():
                try:
                    validate_question_structure(value)
                except ValidationError as e:
                    raise ValidationError({"additional_questions": f'Invalid structure for question "{key}": {str(e)}'})

        # Validate language and original relationships
        if self.lang != "en" and self.original is None:
            raise ValidationError({"original": "Non-English templates must have an original template"})

        if self.lang == "en" and self.original is not None:
            raise ValidationError({"original": "English templates cannot have an original template"})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.original:
            return f"{self.slug} ({self.lang} translation of {self.original.slug})"
        return f"{self.slug} ({self.lang} original)"

    class Meta:
        unique_together = [
            ("original", "lang"),  # Ensure only one translation per language
        ]

    @staticmethod
    def get_template(slug, lang, academy=None):
        """
        Get a SurveyTemplate by slug and language, with optional academy filtering.

        Args:
            slug (str): The template slug to search for
            lang (str): The preferred language code (e.g., 'en', 'es')
            academy (Academy, optional): The academy to filter templates by

        Returns:
            SurveyTemplate: The matching template or None if not found

        Logic:
            1. Try to find a template with the exact slug and language:
               a. If academy is provided, look for templates that either belong to that academy OR are shared
               b. If academy is not provided, only look for shared templates
            2. If not found in the requested language, try English as fallback with the same logic
               a. Check for translations of English templates in the requested language
        """

        # Build the query filter based on whether academy is provided
        if academy:
            # Look for templates that either belong to the academy OR are shared
            academy_filter = Q(academy=academy) | Q(is_shared=True)
        else:
            # Only look for shared templates
            academy_filter = Q(is_shared=True)

        # If slug is None, try to find English template with the same academy filter
        if slug is None:
            template = SurveyTemplate.objects.filter(Q(lang=lang) | Q(lang="en"), is_shared=True).first()

            if template:
                if template.lang == lang:
                    return template

                translation = template.translations.filter(lang=lang).first()
                return translation or template

            return None

        # Try to find exact match by slug and language
        template = SurveyTemplate.objects.filter(slug=slug, lang=lang).filter(academy_filter).first()
        if template:
            return template

        # Try to find English template with the same academy filter
        template = SurveyTemplate.objects.filter(slug=slug, lang="en").filter(academy_filter).first()
        if template:
            # If there's a translation in the requested language
            translation = template.translations.filter(lang=lang).first()
            if translation:
                return translation or template


class AcademyFeedbackSettings(models.Model):
    """Settings for feedback surveys per academy"""

    academy = models.OneToOneField(Academy, on_delete=models.CASCADE, related_name="feedback_settings")

    cohort_survey_template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cohort_survey_academies",
        help_text="Template used for monthly cohort quality surveys, leave empty to disable",
    )

    liveclass_survey_template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="liveclass_survey_academies",
        help_text="Template used for live class quality surveys, leave empty to disable",
    )

    liveclass_survey_cohort_exclusions = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comma separated list of cohort IDs to exclude from live class surveys, leave empty to disable",
    )

    event_survey_template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_survey_academies",
        help_text="Template used for event quality surveys, leave empty to disable",
    )

    mentorship_session_survey_template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentorship_survey_academies",
        help_text="Template used for mentorship session quality surveys, leave empty to disable",
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"Feedback settings for {self.academy.name}"

    def get_excluded_cohort_ids(self):
        """Returns list of excluded cohort IDs for live class surveys"""
        if not self.liveclass_survey_cohort_exclusions:
            return []

        try:
            return [int(x.strip()) for x in self.liveclass_survey_cohort_exclusions.split(",") if x.strip()]
        except ValueError:
            return []

    class Meta:
        verbose_name = "Academy Feedback Settings"
        verbose_name_plural = "Academy Feedback Settings"


class SurveyConfiguration(models.Model):
    class TriggerType(models.TextChoices):
        MODULE_COMPLETION = "module_completed", "Module Completion"
        SYLLABUS_COMPLETION = "syllabus_completed", "Syllabus Completion"
        LEARNPACK_COMPLETION = "learnpack_completed", "Learnpack Completion"
        COURSE_COMPLETION = "course_completed", "Course Completion"

    trigger_type = models.CharField(
        max_length=50,
        choices=TriggerType.choices,
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Realtime trigger type for this configuration (learnpack_completed, course_completed, "
            "module_completed or syllabus_completed). "
            "Only for realtime studies where a modal appears after a user completes an activity. "
            "For email/list-based studies, this can be null."
        ),
    )

    syllabus = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional filter to scope surveys by syllabus/module. "
            "Shape: {'syllabus': '<syllabus_slug>', 'version': <int>, 'module': <int>, 'asset_slug': '<slug>'}. "
            "All keys are optional; if 'module' is omitted, it applies to the whole syllabus/version."
        ),
    )

    template = models.ForeignKey(
        "feedback.SurveyQuestionTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_configurations",
        help_text="Optional questions template. If set, questions are sourced from the template.",
    )
    questions = models.JSONField(help_text="Questions JSON structure (flexible format)")
    is_active = models.BooleanField(default=True)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE, help_text="Used to scope configurations by academy")
    cohorts = models.ManyToManyField(
        Cohort,
        blank=True,
        help_text="If empty, applies to all cohorts. If set, applies only to those cohorts.",
    )
    asset_slugs = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "For learnpacks: if empty, applies to all. If set, applies only to those learnpacks. "
            "Example: ['learnpack-1', 'learnpack-2']"
        ),
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def clean(self):
        if self.asset_slugs and not isinstance(self.asset_slugs, list):
            raise ValidationError("asset_slugs must be a list")

        if self.syllabus and not isinstance(self.syllabus, dict):
            raise ValidationError({"syllabus": "syllabus must be a dictionary"})

        allowed_keys = {"syllabus", "version", "module", "asset_slug"}
        for k in (self.syllabus or {}).keys():
            if k not in allowed_keys:
                raise ValidationError({"syllabus": f"Invalid key: {k}"})

        syllabus_slug = (self.syllabus or {}).get("syllabus")
        if syllabus_slug is not None and not isinstance(syllabus_slug, str):
            raise ValidationError({"syllabus": "'syllabus' must be a string (syllabus slug)"})

        version = (self.syllabus or {}).get("version")
        if version is not None and (not isinstance(version, int) or version < 1):
            raise ValidationError({"syllabus": "'version' must be an integer >= 1"})

        module = (self.syllabus or {}).get("module")
        if module is not None and (not isinstance(module, int) or module < 0):
            raise ValidationError({"syllabus": "'module' must be an integer >= 0"})

        asset_slug = (self.syllabus or {}).get("asset_slug")
        if asset_slug is not None and not isinstance(asset_slug, str):
            raise ValidationError({"syllabus": "'asset_slug' must be a string"})

    def save(self, *args, **kwargs):
        previous_template_id = None
        if self.pk:
            previous_template_id = (
                SurveyConfiguration.objects.filter(pk=self.pk).values_list("template_id", flat=True).first()
            )

        if self.template is not None:
            if previous_template_id != self.template_id:
                self.questions = self.template.questions

            else:
                # Template unchanged: questions must match template exactly
                if self.questions != self.template.questions:
                    raise ValidationError({"questions": "Questions cannot be modified when template is assigned"})

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Survey Configuration: {self.trigger_type} ({self.academy.name})"

    class Meta:
        verbose_name = "Survey Configuration"
        verbose_name_plural = "Survey Configurations"


class SurveyResponse(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        OPENED = "OPENED", "Opened"
        PARTIAL = "PARTIAL", "Partial"
        ANSWERED = "ANSWERED", "Answered"
        EXPIRED = "EXPIRED", "Expired"

    survey_config = models.ForeignKey(SurveyConfiguration, on_delete=models.CASCADE)
    survey_study = models.ForeignKey(
        "feedback.SurveyStudy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_responses",
        help_text="Study/campaign that originated this survey response (optional).",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(null=True, blank=True, editable=False, unique=True)
    trigger_context = models.JSONField(
        help_text="Context that originated the survey (e.g. learnpack_slug, course_slug, cohort_id, etc.)"
    )
    questions_snapshot = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Snapshot of questions used to render/validate this response.",
    )
    answers = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Respuestas del usuario guardadas en BD, null hasta que responda. Formato: {'q1': 5, 'q2': 4, 'q3': 'texto respuesta'}",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    opened_at = models.DateTimeField(null=True, blank=True, default=None, help_text="First time the survey was opened")
    email_opened_at = models.DateTimeField(
        null=True, blank=True, default=None, help_text="First time the survey email was opened"
    )
    answered_at = models.DateTimeField(null=True, blank=True, default=None, help_text="When the survey was answered")

    def save(self, *args, **kwargs):
        if self.token is None:
            self.token = uuid_lib.uuid4()

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Survey Response {self.id} - User: {self.user.email} - Status: {self.status}"

    class Meta:
        verbose_name = "Survey Response"
        verbose_name_plural = "Survey Responses"


class SurveyQuestionTemplate(models.Model):
    """
    Question template for the new SurveyConfiguration/SurveyResponse system.
    NOTE: This is not the legacy `SurveyTemplate` used by the classic NPS Survey/Answer flows.
    """

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, default=None)
    questions = models.JSONField(help_text="Questions JSON structure (same shape as SurveyConfiguration.questions)")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.slug} ({self.id})"

    class Meta:
        verbose_name = "Survey Question Template"
        verbose_name_plural = "Survey Question Templates"


class SurveyStudy(models.Model):
    """
    A study/campaign that groups one or more SurveyConfigurations and provides study-level constraints/stats.
    """

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True, default=None)
    academy = models.ForeignKey(Academy, on_delete=models.CASCADE)

    starts_at = models.DateTimeField(null=True, blank=True, default=None)
    ends_at = models.DateTimeField(null=True, blank=True, default=None)
    max_responses = models.PositiveIntegerField(
        null=True, blank=True, default=None, help_text="Max ANSWERED responses allowed (null = unlimited)"
    )

    survey_configurations = models.ManyToManyField(
        SurveyConfiguration,
        blank=True,
        related_name="survey_studies",
        help_text="Survey configurations that belong to this study",
    )

    stats = models.JSONField(default=dict, blank=True, help_text="Aggregated stats for this study")

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f"{self.slug} ({self.academy.slug})"

    class Meta:
        verbose_name = "Survey Study"
        verbose_name_plural = "Survey Studies"
