import datetime

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

__all__ = ["UserProxy", "CohortUserProxy", "CohortProxy", "Survey", "Answer", "SurveyTemplate"]


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
        raise ValidationError("Value must be a dictionary")

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
            title=strings["en"]["live_class_mentor"]["title"],
            highest=strings["en"]["live_class_mentor"]["highest"],
            lowest=strings["en"]["live_class_mentor"]["lowest"],
            survey_subject=strings["en"]["live_class_mentor"]["survey_subject"],
        ),
    )
    when_asking_mentor_communication = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about mentor communication during class",
        default=dict(
            title=strings["en"]["live_class_mentor_communication"]["title"],
            highest=strings["en"]["live_class_mentor_communication"]["highest"],
            lowest=strings["en"]["live_class_mentor_communication"]["lowest"],
            survey_subject=strings["en"]["live_class_mentor_communication"]["survey_subject"],
        ),
    )
    when_asking_mentor_participation = models.JSONField(
        null=True,
        blank=True,
        validators=[validate_question_structure],
        help_text="Questions to ask about class how the mentor answers and encoursges participation",
        default=dict(
            title=strings["en"]["live_class_mentor_practice"]["title"],
            highest=strings["en"]["live_class_mentor_practice"]["highest"],
            lowest=strings["en"]["live_class_mentor_practice"]["lowest"],
            survey_subject=strings["en"]["live_class_mentor_practice"]["survey_subject"],
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
