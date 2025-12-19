import logging
import re
from datetime import timedelta

from capyc.rest_framework.exceptions import ValidationException
from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework import serializers

from breathecode.admissions.models import Academy, Cohort
from breathecode.monitoring.actions import test_link
from breathecode.services.activecampaign.client import acp_ids
from breathecode.utils import serpy
from breathecode.utils.integer_to_base import to_base

from .models import (
    AcademyAlias,
    ActiveCampaignAcademy,
    Automation,
    Course,
    CourseResaleSettings,
    CourseTranslation,
    FormEntry,
    ShortLink,
    Tag,
)

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

    # New traceability fields
    event = serpy.Field()
    course = serpy.Field()
    downloadable = serpy.Field()
    plan = serpy.Field()
    referrer_user = serpy.Field()
    purpose = serpy.Field()
    notes = serpy.Field()


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
    custom_fields = serpy.MethodField(required=False)

    def get_custom_fields(self, obj):
        if isinstance(obj.custom_fields, dict):
            processed_fields = {}
            for key, value in obj.custom_fields.items():
                if isinstance(value, list):
                    processed_fields[key] = ",".join(map(str, value))
                else:
                    processed_fields[key] = value
            return processed_fields
        return {}


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
    custom_fields = serpy.MethodField(required=False)
    lead_generation_app = LeadgenAppSmallSerializer(required=False)

    def get_cohort(self, obj):
        _cohort = Cohort.objects.filter(slug=obj.ac_expected_cohort).first()
        if _cohort is None:
            return _cohort

        return CohortHookSerializer(_cohort).data

    def get_is_won(self, obj):
        return obj.deal_status == "WON"

    def get_custom_fields(self, obj):
        if isinstance(obj.custom_fields, dict):
            processed_fields = {}
            for key, value in obj.custom_fields.items():
                if isinstance(value, list):
                    processed_fields[key] = ",".join(map(str, value))
                else:
                    processed_fields[key] = value
            return processed_fields
        return {}


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
    custom_fields = serpy.MethodField(required=False)

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

    def get_custom_fields(self, obj):

        if not isinstance(obj.custom_fields, dict):
            return obj.custom_fields

        def convert_dict(input_dict, mapping_dict):
            print(input_dict, mapping_dict)
            # Create an inverse mapping dictionary from the deal_custom_fields
            inverse_mapping = {v: k for k, v in mapping_dict.items()}

            # Create a new dictionary with the converted keys
            converted_dict = {}
            for key, value in input_dict.items():
                if key in inverse_mapping:
                    new_key = inverse_mapping[key]
                    converted_dict[new_key] = value
                else:
                    converted_dict[key] = value

            return converted_dict

        out = convert_dict(obj.custom_fields, acp_ids["deal"])
        return out


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
    featured_assets = serpy.Field()
    description = serpy.Field()
    short_description = serpy.Field()
    lang = serpy.Field()
    course_modules = serpy.Field()
    landing_variables = serpy.Field()
    landing_url = serpy.Field()
    preview_url = serpy.Field()
    video_url = serpy.Field()
    heading = serpy.Field()
    prerequisite = serpy.Field()


class GetCourseSmallSerializer(serpy.Serializer):
    slug = serpy.Field()
    icon_url = serpy.MethodField()
    banner_image = serpy.MethodField()
    academy = serpy.MethodField()
    syllabus = serpy.MethodField()
    color = serpy.MethodField()
    course_translation = serpy.MethodField()
    technologies = serpy.MethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = kwargs.get("context", {})

    def _get_resale_settings(self, obj):
        """
        Helper to get resale settings if the course is being accessed by a reseller.
        Returns CourseResaleSettings if exists, None otherwise.
        """
        academy_id = self.context.get("academy_id")
        if not academy_id:
            return None
        
        return CourseResaleSettings.objects.filter(
            course=obj,
            academy_id=academy_id,
            is_active=True
        ).first()

    def get_icon_url(self, obj):
        """Return icon URL, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.icon_url:
            return resale.icon_url
        return obj.icon_url

    def get_banner_image(self, obj):
        """Return banner image, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.banner_image:
            return resale.banner_image
        return obj.banner_image

    def get_color(self, obj):
        """Return color, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.color:
            return resale.color
        return obj.color

    def get_technologies(self, obj):
        """Return technologies, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.technologies:
            return resale.technologies
        return obj.technologies

    def get_academy(self, obj):
        """Always returns the original course owner ID."""
        return obj.academy.id

    def get_syllabus(self, obj):
        """Always returns original syllabus (content cannot be modified by resellers)."""
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
    syllabus = serpy.MethodField()
    academy = GetAcademySmallSerializer()
    cohort = serpy.MethodField()
    status = serpy.MethodField()
    is_listed = serpy.MethodField()
    visibility = serpy.MethodField()
    plan_slug = serpy.MethodField()
    suggested_plan_addon = serpy.MethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = kwargs.get("context", {})

    def get_syllabus(self, obj):
        return GetSyllabusSmallSerializer(obj.syllabus.all(), many=True).data

    def get_cohort(self, obj):
        if obj.cohort:
            return GetCohortSmallSerializer(obj.cohort, many=False).data

    def get_status(self, obj):
        """Return status, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.status:
            return resale.status
        return obj.status

    def get_is_listed(self, obj):
        """Return is_listed, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.is_listed is not None:
            return resale.is_listed
        return obj.is_listed

    def get_visibility(self, obj):
        """Return visibility, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        if resale and resale.visibility:
            return resale.visibility
        return obj.visibility

    def get_plan_slug(self, obj):
        """Return plan slug, using reseller's custom value if applicable."""
        resale = self._get_resale_settings(obj)
        country_code = (self.context.get("country_code") or "").lower()
        
        # If resale exists and has custom plan settings
        if resale:
            # Check resale plan by country code first
            if country_code and resale.plan_by_country_code and country_code in resale.plan_by_country_code:
                plan_slug = resale.plan_by_country_code.get(country_code)
                if plan_slug:
                    return plan_slug
            
            # Then check resale plan_slug
            if resale.plan_slug:
                return resale.plan_slug
        
        # Fallback to original course plan
        if country_code and obj.plan_by_country_code and country_code in obj.plan_by_country_code:
            plan_slug = obj.plan_by_country_code.get(country_code, "")
            if plan_slug is not None:
                return plan_slug

        return obj.plan_slug

    def get_suggested_plan_addon(self, obj):
        return list(obj.suggested_plan_addon.all().values_list("slug", flat=True))


class CoursePUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = (
            "slug",
            "syllabus",
            "cohort",
            "is_listed",
            "plan_slug",
            "status",
            "color",
            "status_message",
            "visibility",
            "icon_url",
            "banner_image",
            "technologies",
            "has_waiting_list",
        )
        extra_kwargs = {
            "slug": {"required": False},
            "technologies": {"required": False},
            "icon_url": {"required": False},
        }
        read_only_fields = ()


class CourseTranslationPUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseTranslation
        fields = (
            "title",
            "heading",
            "description",
            "short_description",
            "video_url",
            "featured_assets",
            "landing_url",
            "preview_url",
        )


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


class POSTTagSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=True, max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Tag
        fields = ("slug", "tag_type", "description", "automation")
        extra_kwargs = {
            "tag_type": {"required": False, "allow_null": True},
            "automation": {"required": False, "allow_null": True},
        }

    def create(self, validated_data):
        from breathecode.services.activecampaign import ActiveCampaign
        from breathecode.admissions.models import Academy

        academy_id = self.context.get("academy")
        if not academy_id:
            raise ValidationException("Academy ID is required", slug="missing-academy-id")

        academy = Academy.objects.filter(id=academy_id).first()
        if academy is None:
            raise ValidationException(f"Academy {academy_id} not found", slug="academy-not-found")

        slug = validated_data.pop("slug")
        description = validated_data.pop("description", "")

        # Check if tag already exists for this academy (check both relationships)
        existing_tag = Tag.objects.filter(slug=slug).filter(
            Q(ac_academy__academy__id=academy_id) | Q(academy__id=academy_id)
        ).first()
        
        if existing_tag:
            raise ValidationException(
                f"Tag with slug '{slug}' already exists for this academy", slug="tag-already-exists"
            )

        # Try to get ActiveCampaign Academy (optional)
        ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
        
        acp_id = None
        subscribers = 0
        
        # If ActiveCampaign is configured, create tag there
        if ac_academy:
            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            try:
                ac_data = client.create_tag(slug, description=description or "")
                acp_id = ac_data["id"]
                subscribers = 0  # Will be updated on sync
            except Exception as e:
                # Log but don't fail - tag can still be created locally
                logger.warning(f"Failed to create tag in ActiveCampaign: {str(e)}")

        # Create local Tag object
        tag = Tag(
            slug=slug,
            acp_id=acp_id,
            ac_academy=ac_academy,
            academy=academy,  # Direct academy relationship
            subscribers=subscribers,
            description=description,
            **validated_data,
        )
        tag.save()

        return tag


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


class CourseResaleSettingsSerializer(serpy.Serializer):
    """Serializer for GET requests of CourseResaleSettings."""

    id = serpy.Field()
    course = serpy.MethodField()
    academy = AcademySmallSerializer()
    
    # Pricing and plans
    plan_slug = serpy.Field()
    plan_by_country_code = serpy.Field()
    
    # Visual customization
    icon_url = serpy.Field()
    banner_image = serpy.Field()
    color = serpy.Field()
    technologies = serpy.Field()
    
    # Status and visibility
    status = serpy.Field()
    status_message = serpy.Field()
    visibility = serpy.Field()
    is_listed = serpy.Field()
    has_waiting_list = serpy.Field()
    
    # Control
    is_active = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_course(self, obj):
        return {"id": obj.course.id, "slug": obj.course.slug}


class CourseResaleSettingsPOSTSerializer(serializers.ModelSerializer):
    """Serializer for POST requests to create CourseResaleSettings."""

    class Meta:
        model = CourseResaleSettings
        fields = (
            # Pricing and plans
            "plan_slug",
            "plan_by_country_code",
            # Visual customization
            "icon_url",
            "banner_image",
            "color",
            "technologies",
            # Status and visibility
            "status",
            "status_message",
            "visibility",
            "is_listed",
            "has_waiting_list",
            # Control
            "is_active",
        )

    def validate(self, data):
        """Validate course resale settings data."""
        academy = self.context.get("academy")
        course = self.context.get("course")

        if academy is None:
            raise ValidationException("Academy not found in context", slug="academy-not-found")

        if course is None:
            raise ValidationException("Course not found in context", slug="course-not-found")

        # Check if course already has resale settings for this academy
        if CourseResaleSettings.objects.filter(course=course, academy=academy).exists():
            raise ValidationException(
                f"Resale settings already exist for course {course.slug} and academy {academy.slug}",
                slug="resale-settings-already-exist",
                code=400,
            )

        # Check if academy is trying to resell its own course
        if course.academy == academy:
            raise ValidationException(
                "An academy cannot resell its own courses",
                slug="cannot-resell-own-course",
                code=400,
            )

        return data

    def create(self, validated_data):
        """Create CourseResaleSettings instance."""
        academy = self.context.get("academy")
        course = self.context.get("course")

        return CourseResaleSettings.objects.create(course=course, academy=academy, **validated_data)


class CourseResaleSettingsPUTSerializer(serializers.ModelSerializer):
    """Serializer for PUT requests to update CourseResaleSettings."""

    class Meta:
        model = CourseResaleSettings
        fields = (
            # Pricing and plans
            "plan_slug",
            "plan_by_country_code",
            # Visual customization
            "icon_url",
            "banner_image",
            "color",
            "technologies",
            # Status and visibility
            "status",
            "status_message",
            "visibility",
            "is_listed",
            "has_waiting_list",
            # Control
            "is_active",
        )


# ============================================================================
# V2 Serializers - Use ppc_tracking_id instead of gclid
# ============================================================================


class FormEntrySerializerV2(serpy.Serializer):
    """V2 serializer that uses ppc_tracking_id instead of gclid"""
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    ppc_tracking_id = serpy.MethodField()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    utm_placement = serpy.Field()
    utm_term = serpy.Field()
    utm_plan = serpy.Field()
    sex = serpy.Field()
    tags = serpy.Field()
    storage_status = serpy.Field()
    country = serpy.Field()
    lead_type = serpy.Field()
    academy = AcademySmallSerializer(required=False)
    client_comments = serpy.Field(required=False)
    created_at = serpy.Field()
    custom_fields = serpy.MethodField(required=False)

    def get_ppc_tracking_id(self, obj):
        """Map gclid field to ppc_tracking_id"""
        return obj.gclid

    def get_custom_fields(self, obj):
        if isinstance(obj.custom_fields, dict):
            processed_fields = {}
            for key, value in obj.custom_fields.items():
                if isinstance(value, list):
                    processed_fields[key] = ",".join(map(str, value))
                else:
                    processed_fields[key] = value
            return processed_fields
        return {}


class PostFormEntrySerializerV2(serializers.ModelSerializer):
    """
    V2 serializer for creating form entries.
    Accepts ppc_tracking_id instead of gclid - no backward compatibility.
    """

    ppc_tracking_id = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = FormEntry
        exclude = ()
        read_only_fields = ["id"]
        extra_kwargs = {
            "gclid": {"write_only": True},  # Hide gclid from input, we use ppc_tracking_id instead
        }

    def to_internal_value(self, data):
        """Map ppc_tracking_id to gclid before validation"""
        if "ppc_tracking_id" in data:
            # Create a copy to avoid mutating the original
            data = data.copy()
            data["gclid"] = data.pop("ppc_tracking_id")
        return super().to_internal_value(data)

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
