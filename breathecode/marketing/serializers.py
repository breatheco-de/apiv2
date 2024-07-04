import logging
import re
from datetime import timedelta

from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework import serializers

from breathecode.admissions.models import Academy, Cohort
from breathecode.monitoring.actions import test_link
from breathecode.utils import serpy
from breathecode.utils.integer_to_base import to_base
from capyc.rest_framework.exceptions import ValidationException

from .models import AcademyAlias, ActiveCampaignAcademy, Automation, CourseTranslation, FormEntry, ShortLink, Tag

logger = logging.getLogger(__name__)


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class LeadgenAppSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    app_id = serpy.Field()


class AcademyAliasSmallSerializer(serpy.Serializer):
    academy = AcademySmallSerializer()
    slug = serpy.Field()
    active_campaign_slug = serpy.Field()


class ShortlinkSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    destination = serpy.Field()
    hits = serpy.Field()
    private = serpy.Field()
    destination_status = serpy.Field()
    destination_status_text = serpy.Field()
    lastclick_at = serpy.Field()
    active = serpy.Field()

    utm_content = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    id = serpy.Field()


class UTMSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    utm_type = serpy.Field()
    updated_at = serpy.Field()


class AutomationSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()


class ActiveCampaignAcademyBigSerializer(serpy.Serializer):
    id = serpy.Field()
    ac_key = serpy.Field()
    ac_url = serpy.Field()
    academy = AcademySmallSerializer()
    duplicate_leads_delta_avoidance = serpy.Field()
    sync_status = serpy.Field()
    sync_message = serpy.Field()
    last_interaction_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    event_attendancy_automation = AutomationSmallSerializer(required=False)


class DownloadableSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    destination_url = serpy.Field()
    preview_url = serpy.Field()


class SyllabusScheduleHookSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    syllabus = serpy.MethodField(required=False)

    def get_syllabus(self, obj):
        return obj.syllabus.name if obj.syllabus else None


class GetCohortSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CohortHookSerializer(GetCohortSmallSerializer):
    schedule = SyllabusScheduleHookSerializer(required=False)
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()


class TagSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    tag_type = serpy.Field()
    subscribers = serpy.Field()
    disputed_at = serpy.Field()
    disputed_reason = serpy.Field()
    automation = AutomationSmallSerializer(required=False)
    created_at = serpy.Field()


class FormEntrySerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()
    sex = serpy.Field()
    custom_fields = serpy.Field()
    tags = serpy.Field()
    storage_status = serpy.Field()
    country = serpy.Field()
    lead_type = serpy.Field()
    academy = AcademySmallSerializer(required=False)
    client_comments = serpy.Field(required=False)
    created_at = serpy.Field()
    custom_fields = serpy.Field()


class FormEntryHookSerializer(serpy.Serializer):
    id = serpy.Field()
    attribution_id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    sex = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    phone = serpy.Field()
    deal_status = serpy.Field()
    current_download = serpy.Field()
    contact = serpy.Field()
    client_comments = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    fb_ad_id = serpy.Field()
    fb_adgroup_id = serpy.Field()
    fb_form_id = serpy.Field()
    fb_leadgen_id = serpy.Field()
    fb_page_id = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_content = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()
    custom_fields = serpy.Field()
    referral_key = serpy.Field()
    tags = serpy.Field()
    automations = serpy.Field()
    storage_status = serpy.Field()
    storage_status_text = serpy.Field()
    country = serpy.Field()
    state = serpy.Field()
    city = serpy.Field()
    street_address = serpy.Field()
    latitude = serpy.Field()
    longitude = serpy.Field()
    zip_code = serpy.Field()
    ac_expected_cohort = serpy.Field()
    browser_lang = serpy.Field()
    lead_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    won_at = serpy.Field()
    sentiment = serpy.Field()
    ac_deal_location = serpy.Field()
    ac_deal_course = serpy.Field()
    ac_deal_owner_full_name = serpy.Field()
    ac_deal_owner_id = serpy.Field()
    ac_contact_id = serpy.Field()
    ac_deal_id = serpy.Field()
    ac_deal_amount = serpy.Field()
    ac_deal_currency_code = serpy.Field()
    ac_expected_cohort = serpy.Field()
    ac_expected_cohort_date = serpy.Field()

    cohort = serpy.MethodField(required=False)
    is_won = serpy.MethodField(required=False)

    def get_cohort(self, obj):
        _cohort = Cohort.objects.filter(slug=obj.ac_expected_cohort).first()
        if _cohort is None:
            return _cohort

        return CohortHookSerializer(_cohort).data

    def get_is_won(self, obj):
        return obj.deal_status == "WON"


class FormEntrySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    sex = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    phone = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_content = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()
    tags = serpy.Field()
    storage_status = serpy.Field()
    storage_status_text = serpy.Field()
    country = serpy.Field()
    ac_expected_cohort = serpy.Field()
    lead_type = serpy.Field()
    created_at = serpy.Field()
    user = UserSmallSerializer(required=False)


class FormEntryBigSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    ac_expected_cohort = serpy.Field()
    ac_contact_id = serpy.Field()
    ac_deal_id = serpy.Field()
    sex = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    phone = serpy.Field()
    deal_status = serpy.Field()
    current_download = serpy.Field()
    contact = serpy.Field()
    client_comments = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    fb_ad_id = serpy.Field()
    fb_adgroup_id = serpy.Field()
    fb_form_id = serpy.Field()
    fb_leadgen_id = serpy.Field()
    fb_page_id = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_content = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()
    custom_fields = serpy.Field()
    referral_key = serpy.Field()
    tags = serpy.Field()
    automations = serpy.Field()
    tag_objects = serpy.MethodField()
    automation_objects = serpy.MethodField()
    storage_status = serpy.Field()
    storage_status_text = serpy.Field()
    country = serpy.Field()
    state = serpy.Field()
    city = serpy.Field()
    street_address = serpy.Field()
    latitude = serpy.Field()
    longitude = serpy.Field()
    zip_code = serpy.Field()
    ac_expected_cohort = serpy.Field()
    browser_lang = serpy.Field()
    lead_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    won_at = serpy.Field()
    sentiment = serpy.Field()
    ac_deal_location = serpy.Field()
    ac_deal_course = serpy.Field()
    ac_deal_owner_full_name = serpy.Field()
    ac_deal_owner_id = serpy.Field()
    ac_expected_cohort_date = serpy.Field()
    academy = AcademySmallSerializer(required=False)
    lead_generation_app = LeadgenAppSmallSerializer(required=False)
    user = UserSmallSerializer(required=False)

    def get_tag_objects(self, obj):
        tag_ids = []
        if obj.tags is not None:
            tag_ids = obj.tags.split(",")

        tags = Tag.objects.filter(slug__in=tag_ids, ac_academy__academy=obj.calculate_academy())
        return TagSmallSerializer(tags, many=True).data

    def get_automation_objects(self, obj):
        automation_ids = []
        if obj.automations is not None:
            automation_ids = obj.automations.split(",")

        automations = Automation.objects.filter(slug__in=automation_ids, ac_academy__academy=obj.calculate_academy())
        return AutomationSmallSerializer(automations, many=True).data


class GetAcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    icon_url = serpy.Field()


class GetSyllabusSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo = serpy.Field()


class GetCourseTranslationSerializer(serpy.Serializer):
    title = serpy.Field()
    description = serpy.Field()
    short_description = serpy.Field()
    lang = serpy.Field()
    course_modules = serpy.Field()
    landing_variables = serpy.Field()
    landing_url = serpy.Field()
    video_url = serpy.Field()


class GetCourseSmallSerializer(serpy.Serializer):
    slug = serpy.Field()
    icon_url = serpy.Field()
    academy = serpy.MethodField()
    syllabus = serpy.MethodField()
    color = serpy.Field()
    course_translation = serpy.MethodField()
    technologies = serpy.Field()

    def get_academy(self, obj):
        return obj.academy.id

    def get_syllabus(self, obj):
        return [x for x in obj.syllabus.all().values_list("id", flat=True)]

    def get_course_translation(self, obj):
        query_args = []
        query_kwargs = {"course": obj}
        obj.lang = obj.lang or "en"

        query_args.append(Q(lang=obj.lang) | Q(lang=obj.lang[:2]) | Q(lang__startswith=obj.lang[:2]))

        item = CourseTranslation.objects.filter(*query_args, **query_kwargs).first()
        if item:
            return GetCourseTranslationSerializer(item, many=False).data

        return None


class GetCourseSerializer(GetCourseSmallSerializer):
    plan_slug = serpy.Field()
    syllabus = serpy.MethodField()
    academy = GetAcademySmallSerializer()
    cohort = serpy.MethodField()
    status = serpy.Field()
    visibility = serpy.Field()

    def get_syllabus(self, obj):
        return GetSyllabusSmallSerializer(obj.syllabus.all(), many=True).data

    def get_cohort(self, obj):
        if obj.cohort:
            return GetCohortSmallSerializer(obj.cohort, many=False).data


class PostFormEntrySerializer(serializers.ModelSerializer):

    class Meta:
        model = FormEntry
        exclude = ()
        read_only_fields = ["id"]

    def create(self, validated_data):

        academy = None
        if "location" in validated_data:
            alias = AcademyAlias.objects.filter(active_campaign_slug=validated_data["location"]).first()
            if alias is not None:
                academy = alias.academy
            else:
                academy = Academy.objects.filter(active_campaign_slug=validated_data["location"]).first()

        # copy the validated data just to do small last minute corrections
        data = validated_data.copy()

        # "us" language will become "en" language, its the right lang code
        if "language" in data and data["language"] == "us":
            data["language"] = "en"

        if "tag_objects" in data and data["tag_objects"] != "":
            tag_ids = data["tag_objects"].split(",")
            data["tags"] = Tag.objects.filter(id__in=tag_ids)

        result = super().create({**data, "academy": academy})
        return result


class ShortLinkSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, default=None)

    class Meta:
        model = ShortLink
        exclude = ("academy", "author", "hits", "destination_status", "destination_status_text")

    def validate(self, data):

        if "slug" in data and data["slug"] is not None:

            if not re.match(r"^[-\w]+$", data["slug"]):
                raise ValidationException(
                    f'Invalid link slug {data["slug"]}, should only contain letters, numbers and slash "-"',
                    slug="invalid-slug-format",
                )

            link = ShortLink.objects.filter(slug=data["slug"]).first()
            if link is not None and (self.instance is None or self.instance.id != link.id):
                raise ValidationException(
                    f'Shortlink with slug {data["slug"]} already exists', slug="shortlink-already-exists"
                )
        elif self.instance is None:
            # only if it's being created I will pick a new slug, if not I will allow it to have the original slug
            latest_url = ShortLink.objects.all().last()
            if latest_url is None:
                data["slug"] = "L" + to_base(1)
            else:
                data["slug"] = "L" + to_base(latest_url.id + 1)

        status = test_link(data["destination"])
        if status["status_code"] < 200 or status["status_code"] > 299:
            raise ValidationException(f'Destination URL is invalid, returning status {status["status_code"]}')

        academy = Academy.objects.filter(id=self.context["academy"]).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy"]} not found', slug="academy-not-found")

        if self.instance is not None:  # creating a new link (instead of updating)
            utc_now = timezone.now()
            days_ago = self.instance.created_at + timedelta(days=1)
            if days_ago < utc_now and (
                self.instance.destination != data["destination"] or self.instance.slug != data["slug"]
            ):
                raise ValidationException(
                    "You cannot update or delete short links that have been created more than 1 day ago, create a new link instead",
                    slug="update-days-ago",
                )

        return {**data, "academy": academy}

    def create(self, validated_data):

        return ShortLink.objects.create(**validated_data, author=self.context.get("request").user)


class TagListSerializer(serializers.ListSerializer):

    def update(self, instances, validated_data):

        instance_hash = {index: instance for index, instance in enumerate(instances)}

        result = [self.child.update(instance_hash[index], attrs) for index, attrs in enumerate(validated_data)]

        return result


class PUTTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        exclude = ("slug", "acp_id", "subscribers", "ac_academy", "created_at", "updated_at")
        list_serializer_class = TagListSerializer


class PUTAutomationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)

    class Meta:
        model = Automation
        exclude = ("acp_id", "ac_academy", "created_at", "updated_at", "entered", "exited")
        list_serializer_class = TagListSerializer


class ActiveCampaignAcademySerializer(serializers.ModelSerializer):

    class Meta:
        model = ActiveCampaignAcademy
        exclude = ("academy",)

    def validate(self, data):

        academy = Academy.objects.filter(id=self.context["academy"]).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy"]} not found', slug="academy-not-found")

        return {**data, "academy": academy}

    def create(self, validated_data):
        return ActiveCampaignAcademy.objects.create(**validated_data)
