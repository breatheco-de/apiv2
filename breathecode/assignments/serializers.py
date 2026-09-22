import json
import logging
import os

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from rest_framework import serializers

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import Cohort, CohortUser
from breathecode.admissions.services.completion import get_effective_assets_by_type_for_cohort_user
from breathecode.authenticate.models import ProfileAcademy, Token
from breathecode.utils import serpy

from .models import AssignmentTelemetry, FinalProject, Task, UserAttachment

logger = logging.getLogger(__name__)


class ProfileSmallSerializer(serpy.Serializer):
    avatar_url = serpy.Field()


class UserMediumSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = ProfileSmallSerializer(required=False)


class UserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class UserHookSerializer(UserSmallSerializer):
    email = serpy.Field()


class CohortSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class TaskAttachmentSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    url = serpy.Field()
    mime = serpy.Field()


class RepositoryDeletionOrderSerializer(serpy.Serializer):
    user = UserSmallSerializer()
    id = serpy.Field()
    repository_name = serpy.Field()
    repository_user = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    starts_transferring_at = serpy.Field()


class LearnPackWebhookSerializer(serpy.Serializer):
    id = serpy.Field()
    is_streaming = serpy.Field()
    event = serpy.Field()
    asset_id = serpy.Field()
    learnpack_package_id = serpy.Field()
    payload = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    student = UserSmallSerializer(required=False)
    created_at = serpy.Field()
    updated_at = serpy.Field()


class TaskGETSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    description = serpy.Field()
    revision_status = serpy.Field()
    github_url = serpy.Field()
    live_url = serpy.Field()
    task_type = serpy.Field()
    user = UserSmallSerializer()
    opened_at = serpy.Field()
    read_at = serpy.Field()
    reviewed_at = serpy.Field()
    delivered_at = serpy.Field()
    cohort = CohortSmallSerializer(required=False)
    assignment_telemetry = serpy.MethodField()

    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_assignment_telemetry(self, obj):
        telemetry = AssignmentTelemetry.objects.filter(user=obj.user, asset_slug=obj.associated_slug).first()
        if telemetry is not None:
            return telemetry.telemetry
        # Fallback: LearnPack stores telemetry under the canonical translation slug,
        # which may differ from task.associated_slug while Task.telemetry is still linked.
        if obj.telemetry_id is not None and obj.telemetry is not None:
            return obj.telemetry.telemetry
        return None

class TaskUserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    description = serpy.Field()
    revision_status = serpy.Field()
    github_url = serpy.Field()
    live_url = serpy.Field()
    task_type = serpy.Field()
    opened_at = serpy.Field()
    read_at = serpy.Field()
    reviewed_at = serpy.Field()
    delivered_at = serpy.Field()
    cohort = CohortSmallSerializer(required=False)

    created_at = serpy.Field()
    updated_at = serpy.Field()

class TaskHookSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    description = serpy.Field()
    revision_status = serpy.Field()
    github_url = serpy.Field()
    live_url = serpy.Field()
    task_type = serpy.Field()
    user = UserSmallSerializer()
    opened_at = serpy.Field()
    read_at = serpy.Field()
    reviewed_at = serpy.Field()
    delivered_at = serpy.Field()
    cohort = CohortSmallSerializer(required=False)
    assignment_telemetry = serpy.MethodField()

    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_assignment_telemetry(self, obj):
        telemetry = AssignmentTelemetry.objects.filter(user=obj.user, asset_slug=obj.associated_slug).first()
        if telemetry is not None:
            return telemetry.telemetry
        # Fallback: LearnPack stores telemetry under the canonical translation slug,
        # which may differ from task.associated_slug while Task.telemetry is still linked.
        if obj.telemetry_id is not None and obj.telemetry is not None:
            return obj.telemetry.telemetry
        return None


class TaskStatusUpdatedHookSerializer(TaskHookSerializer):
    """Payload for assignment.assignment_status_updated, including module and syllabus progress."""

    user = UserHookSerializer()
    cohort = serpy.MethodField()
    module = serpy.MethodField()
    syllabus = serpy.MethodField()
    plan_slugs = serpy.MethodField()

    def get_cohort(self, obj):
        cohort = getattr(obj, "cohort", None)
        if cohort is None:
            return None

        payload = {"id": cohort.id, "name": cohort.name, "slug": cohort.slug}
        macro = self._macro(obj)
        if macro is not None:
            payload["macro"] = macro
        return payload

    def get_module(self, obj):
        return self._progress(obj)["module"]

    def get_syllabus(self, obj):
        return self._progress(obj)["syllabus"]

    def get_plan_slugs(self, obj):
        from breathecode.payments.models import PlanFinancing, Subscription

        slugs = set(
            Subscription.objects.filter(user_id=obj.user_id, status=Subscription.Status.ACTIVE).values_list(
                "plans__slug", flat=True
            )
        )
        slugs.update(
            PlanFinancing.objects.filter(
                user_id=obj.user_id,
                status__in=[PlanFinancing.Status.ACTIVE, PlanFinancing.Status.FULLY_PAID],
            ).values_list("plans__slug", flat=True)
        )
        slugs.discard(None)
        return sorted(slugs)

    def _macro_cohort(self, obj):
        cached = getattr(self, "_macro_cohort_cache", None)
        if cached is not None and cached[0] == obj.pk:
            return cached[1]

        macro = None
        if obj.cohort_id is not None:
            cohort_user = (
                CohortUser.objects.filter(user_id=obj.user_id, cohort_id=obj.cohort_id)
                .select_related("source_macro_cohort")
                .first()
            )
            macro = cohort_user.source_macro_cohort if cohort_user is not None else None
            if macro is None:
                parents = list(
                    Cohort.objects.filter(micro_cohorts=obj.cohort_id, cohortuser__user_id=obj.user_id)
                    .distinct()
                    .order_by("id")[:2]
                )
                macro = parents[0] if len(parents) == 1 else None

        self._macro_cohort_cache = (obj.pk, macro)
        return macro

    def _macro(self, obj):
        macro = self._macro_cohort(obj)
        if macro is None:
            return None
        return {"id": macro.id, "name": macro.name, "slug": macro.slug}

    def _syllabus_progress_field(self, obj):
        return "micro_progress" if self._macro_cohort(obj) is not None else "progress"

    def _progress(self, obj):
        cached = getattr(self, "_progress_cache", None)
        if cached is not None and cached[0] == obj.pk:
            return cached[1]

        progress_field = self._syllabus_progress_field(obj)
        empty_syllabus = {"completed": False, progress_field: None}
        if self._macro_cohort(obj) is not None:
            empty_syllabus["macro_progress"] = self._macro_progress_ratio(obj)
        result = {"module": None, "syllabus": empty_syllabus}
        cohort = getattr(obj, "cohort", None)
        if cohort is not None and getattr(cohort, "syllabus_version_id", None):
            from breathecode.certificate.actions import syllabus_weeks_to_days
            from breathecode.feedback.actions import _find_module_for_asset_in_syllabus, _get_module_assets_from_syllabus

            syllabus_version = cohort.syllabus_version
            module_index = _find_module_for_asset_in_syllabus(syllabus_version, obj.associated_slug)
            if module_index is not None:
                raw = syllabus_version.json
                syllabus_json = json.loads(raw) if isinstance(raw, str) else (raw or {})
                days = syllabus_weeks_to_days(syllabus_json).get("days") or []
                syllabus_slugs = self._slugs_from_syllabus_version(syllabus_version)
                module_slugs = list(dict.fromkeys(_get_module_assets_from_syllabus(syllabus_version, module_index)))
                done = set(
                    Task.objects.filter(
                        user_id=obj.user_id,
                        cohort_id=cohort.id,
                        associated_slug__in=syllabus_slugs,
                        task_status=Task.TaskStatus.DONE,
                    ).values_list("associated_slug", flat=True)
                )
                syllabus = {
                    "completed": bool(syllabus_slugs) and all(slug in done for slug in syllabus_slugs),
                    progress_field: self._progress_ratio(syllabus_slugs, done),
                }
                if self._macro_cohort(obj) is not None:
                    syllabus["macro_progress"] = self._macro_progress_ratio(obj)
                result = {
                    "module": {
                        "completed": bool(module_slugs) and all(slug in done for slug in module_slugs),
                        "name": self._module_label(days, module_index),
                        "progress": self._progress_ratio(module_slugs, done),
                    },
                    "syllabus": syllabus,
                }

        self._progress_cache = (obj.pk, result)
        return result

    def _slugs_from_syllabus_version(self, syllabus_version):
        from breathecode.certificate.actions import syllabus_weeks_to_days
        from breathecode.feedback.actions import _get_module_assets_from_syllabus

        if syllabus_version is None:
            return []
        raw = syllabus_version.json
        syllabus_json = json.loads(raw) if isinstance(raw, str) else (raw or {})
        days = syllabus_weeks_to_days(syllabus_json).get("days") or []
        slugs = []
        for index in range(len(days)):
            slugs.extend(_get_module_assets_from_syllabus(syllabus_version, index))
        return list(dict.fromkeys(slugs))

    def _macro_progress_ratio(self, obj):
        macro = self._macro_cohort(obj)
        if macro is None:
            return None

        micros = list(macro.micro_cohorts.select_related("syllabus_version").all())
        if obj.cohort is not None and all(micro.id != obj.cohort_id for micro in micros):
            micros.append(obj.cohort)

        slugs = []
        cohort_ids = []
        for micro in micros:
            cohort_ids.append(micro.id)
            slugs.extend(self._slugs_from_syllabus_version(getattr(micro, "syllabus_version", None)))
        slugs = list(dict.fromkeys(slugs))
        if not slugs:
            return None

        done = set(
            Task.objects.filter(
                user_id=obj.user_id,
                cohort_id__in=cohort_ids,
                associated_slug__in=slugs,
                task_status=Task.TaskStatus.DONE,
            ).values_list("associated_slug", flat=True)
        )
        return self._progress_ratio(slugs, done)

    def _module_label(self, days, module_index):
        label = days[module_index].get("label") if module_index < len(days) else None
        if isinstance(label, dict):
            label = label.get("en") or label.get("es")
        if isinstance(label, str) and label.strip():
            return label.strip()
        return None

    def _progress_ratio(self, slugs, done):
        if not slugs:
            return None
        finished = sum(1 for slug in slugs if slug in done)
        return round(finished / len(slugs), 4)


class TaskGETSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    description = serpy.Field()
    revision_status = serpy.Field()
    github_url = serpy.Field()
    live_url = serpy.Field()
    task_type = serpy.Field()
    delivered_at = serpy.Field()

    created_at = serpy.Field()
    updated_at = serpy.Field()


class TaskGETDeliverSerializer(TaskGETSerializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    delivery_url = serpy.MethodField()

    def get_delivery_url(self, obj):
        token, created = Token.get_or_create(obj.user, token_type="short")
        return os.getenv("API_URL") + f"/v1/assignment/task/{str(obj.id)}/deliver/{token}"


class PostTaskListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        instances = []
        for item in validated_data:
            instance = self.child.create(item)
            if instance is not None:
                instances.append(instance)
        return instances


class PostTaskSerializer(serializers.ModelSerializer):
    task_status = serializers.CharField(read_only=True)
    revision_status = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        exclude = ("user",)
        list_serializer_class = PostTaskListSerializer

    def validate(self, data):

        user = User.objects.filter(id=self.context["user_id"]).first()
        if user is None:
            raise ValidationException("User does not exists")

        # the teacher shouldn't be allowed to approve a project that isn't done
        if (
            "associated_slug" in data
            and "task_status" in data
            and "revision_status" in data
            and data["task_status"] == "PENDING"
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException("Only tasks that are DONE should be approved by the teacher")

        return super(PostTaskSerializer, self).validate({**data, "user": user})

    def create(self, validated_data):

        _task = Task.objects.filter(
            associated_slug=validated_data["associated_slug"],
            task_type=validated_data["task_type"],
            user__id=validated_data["user"].id,
        )

        # optional cohort parameter
        if "cohort" not in validated_data:
            _task = _task.filter(cohort__isnull=True)
        else:
            _task = _task.filter(cohort=validated_data["cohort"])

        _task = _task.first()

        # avoid creating a task twice, if the user already has it it will be re-used.
        if _task is not None:
            return _task

        cohort = validated_data.get("cohort")
        user = validated_data["user"]
        if cohort is not None:
            cohort_user = CohortUser.objects.filter(user=user, cohort=cohort).first()
            assets_by_type = (
                get_effective_assets_by_type_for_cohort_user(cohort_user) if cohort_user is not None else None
            )
            if assets_by_type is not None:
                allowed = assets_by_type.get(validated_data["task_type"], set())
                slug = validated_data["associated_slug"]
                if slug not in allowed:
                    logger.info(
                        "Skipping task create slug=%s task_type=%s cohort_user_id=%s source_macro_cohort_id=%s",
                        slug,
                        validated_data["task_type"],
                        cohort_user.id,
                        cohort_user.source_macro_cohort_id,
                    )
                    return None

        instance = Task.objects.create(**validated_data)

        return instance


class AttachmentListSerializer(serializers.ListSerializer):

    def update(self, instance, validated_data):
        ret = []

        for data in validated_data:
            item = [x for x in instance if "id" in data and x.id == data["id"]]
            item = item[0] if len(item) else None

            if "id" in data and not data["id"]:
                del data["id"]

            if "id" in data:
                ret.append(self.child.update(item, data))
            else:
                ret.append(self.child.create(data))

        return ret


class UserAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    url = serializers.CharField(required=False)
    hash = serializers.CharField()
    slug = serializers.SlugField()
    mime = serializers.CharField()
    name = serializers.CharField()

    class Meta:
        model = UserAttachment
        fields = ("id", "url", "hash", "slug", "mime", "name", "user")
        exclude = ()
        list_serializer_class = AttachmentListSerializer


class PUTTaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)
    associated_slug = serializers.CharField(read_only=True)
    task_type = serializers.CharField(read_only=True)
    task_status = serializers.CharField(required=False)
    flags = serializers.JSONField(required=False)

    class Meta:
        model = Task
        exclude = ("user",)

    def validate(self, data):

        if self.instance.user.id != self.context["request"].user.id:
            if "task_status" in data and data["task_status"] != self.instance.task_status:
                raise ValidationException(
                    "Only the task owner can modify its status",
                    slug="put-task-status-of-other-user",
                )
            if "live_url" in data and data["live_url"] != self.instance.live_url:
                raise ValidationException(
                    "Only the task owner can modify its live_url", slug="put-live-url-of-other-user"
                )
            if "github_url" in data and data["github_url"] != self.instance.github_url:
                raise ValidationException(
                    "Only the task owner can modify its github_url", slug="put-github-url-of-other-user"
                )

        # the teacher shouldn't be allowed to approve a project that isn't done
        if (
            "task_status" in data
            and "revision_status" in data
            and data["task_status"] == "PENDING"
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException(
                "Only tasks that are DONE should be approved by the teacher", slug="task-marked-approved-when-pending"
            )
        if (
            self.instance.task_status == "PENDING"
            and "revision_status" in data
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException(
                "Only tasks that are DONE should be approved by the teacher", slug="task-marked-approved-when-pending"
            )

        if "revision_status" in data and data["revision_status"] != self.instance.revision_status:
            student_cohorts = CohortUser.objects.filter(user__id=self.instance.user.id, role="STUDENT").values_list(
                "cohort__id", flat=True
            )
            student_academies = CohortUser.objects.filter(user__id=self.instance.user.id, role="STUDENT").values_list(
                "cohort__academy__id", flat=True
            )

            # the logged in user could be a teacher from the same cohort as the student
            teacher = CohortUser.objects.filter(
                cohort__id__in=student_cohorts,
                role__in=["TEACHER", "ASSISTANT"],
                user__id=self.context["request"].user.id,
            ).first()

            # the logged in user could be a staff member from the same academy that the student belongs
            staff = ProfileAcademy.objects.filter(
                academy__id__in=student_academies, user__id=self.context["request"].user.id
            ).first()

            # task owner should only be able to mark revision status to PENDING
            if data["revision_status"] != "PENDING" and staff is None and teacher is None:
                raise ValidationException(
                    "Only staff members or teachers from the same academy as this student can update the "
                    "review status",
                    slug="editing-revision-status-but-is-not-teacher-or-assistant",
                )

        return data

    def update(self, instance, validated_data):
        if (
            "opened_at" in validated_data
            and validated_data["opened_at"] is not None
            and (instance.opened_at is None or validated_data["opened_at"] > instance.opened_at)
        ):
            tasks_activity.add_activity.delay(
                self.context["request"].user.id,
                "read_assignment",
                related_type="assignments.Task",
                related_id=instance.id,
            )

        if "revision_status" in validated_data and validated_data["revision_status"] != instance.revision_status:
            tasks_activity.add_activity.delay(
                self.context["request"].user.id,
                "assignment_review_status_updated",
                related_type="assignments.Task",
                related_id=instance.id,
            )

        # The student is delivering the task?
        if "task_status" in validated_data and validated_data["task_status"] != instance.task_status:
            tasks_activity.add_activity.delay(
                self.context["request"].user.id,
                "assignment_status_updated",
                related_type="assignments.Task",
                related_id=instance.id,
            )

        # Auto-ignore projects on delivery if feature flag is enabled
        if (
            "task_status" in validated_data
            and validated_data["task_status"] == "DONE"
            and instance.task_status != "DONE"
            and instance.task_type == "PROJECT"
            and instance.cohort
            and instance.user.id == self.context["request"].user.id
        ):
            from breathecode.admissions.utils.academy_features import has_feature_flag
            from django.utils import timezone

            revision_status_set = "revision_status" in validated_data
            revision_status_value = validated_data.get("revision_status")
            
            should_auto_ignore = (
                not revision_status_set or revision_status_value in (None, "PENDING", "")
            )
            
            if should_auto_ignore:
                auto_ignore_enabled = has_feature_flag(
                    instance.cohort.academy, "certificate.auto_ignore_projects_on_delivery", default=False
                )
                
                if auto_ignore_enabled:
                    validated_data["revision_status"] = "IGNORED"
                    validated_data["reviewed_at"] = timezone.now()

        if (
            "task_status" in validated_data
            and validated_data["task_status"] == "DONE"
            and validated_data.get("revision_status") != "APPROVED"
            and "flags" in validated_data
        ):
            print(validated_data)
            from breathecode.assignments.tasks import async_validate_flags

            async_validate_flags.delay(instance.id, instance.associated_slug, validated_data["flags"])

        result = super().update(instance, validated_data)
        
        return result


class FinalProjectGETSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    repo_owner = UserSmallSerializer(required=False)
    name = serpy.Field()
    one_line_desc = serpy.Field()
    description = serpy.Field()

    project_status = serpy.Field()
    revision_status = serpy.Field()
    visibility_status = serpy.Field()

    repo_url = serpy.Field()
    public_url = serpy.Field()
    logo_url = serpy.Field()
    screenshot = serpy.Field()
    slides_url = serpy.Field()
    video_demo_url = serpy.Field()

    cohort = CohortSmallSerializer(required=False)

    created_at = serpy.Field()
    updated_at = serpy.Field()

    members = serpy.MethodField()

    def get_members(self, obj):
        return [UserMediumSerializer(m).data for m in obj.members.all()]


class PostFinalProjectSerializer(serializers.ModelSerializer):
    project_status = serializers.CharField(read_only=True)
    revision_status = serializers.CharField(read_only=True)
    visibility_status = serializers.CharField(read_only=True)

    class Meta:
        model = FinalProject
        exclude = ("repo_owner",)

    def validate(self, data):

        user = User.objects.filter(id=self.context["user_id"]).first()
        if user is None:
            raise ValidationException("User does not exists")

        # the teacher shouldn't be allowed to approve a project that isn't done
        if (
            "project_status" in data
            and "revision_status" in data
            and data["project_status"] == "PENDING"
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException("Only projects that are DONE should be approved")

        if "cohort" not in data or data["cohort"] is None:
            raise ValidationException("Missing cohort id for this project")
        else:
            total_students = CohortUser.objects.filter(
                user__id__in=[m.id for m in data["members"]], cohort__id=data["cohort"].id, role="STUDENT"
            ).count()
            if "members" in data and len(data["members"]) != total_students:
                raise ValidationException(f'Project members must be students on this cohort {data["cohort"].name}')

        if "repo_url" not in data:
            raise ValidationException("Missing repository URL")
        else:
            proj = FinalProject.objects.filter(repo_url=data["repo_url"]).first()
            if proj is not None:
                raise ValidationException(f"There is another project already with this repository: {proj.name}")

        return super(PostFinalProjectSerializer, self).validate({**data, "repo_owner": user})

    def create(self, validated_data):

        members = validated_data.pop("members")
        project = FinalProject.objects.create(**validated_data)
        project.members.set(members)
        return project


class PUTFinalProjectSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    one_line_desc = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    repo_url = serializers.CharField(read_only=True)

    class Meta:
        model = FinalProject
        exclude = ("repo_owner",)

    def validate(self, data):
        user = self.context["request"].user

        if "repo_url" in data and data["repo_url"] != self.instance.repo_url:
            raise ValidationException(
                "Repository URL cannot be updated, delete the project instead", slug="put-update-repo-url"
            )

        exists = self.instance.members.filter(id=user.id).first()
        if exists is None:
            for field_name in ["project_status"]:
                if field_name in data and data[field_name] != getattr(self.instance, field_name):
                    raise ValidationException(
                        f"Only the project members can modify its {field_name}",
                        slug="put-project-property-from-none-members",
                    )

        if "members" in data:
            total_students = CohortUser.objects.filter(
                user__id__in=[m.id for m in data["members"]], cohort__id=data["cohort"].id, role="STUDENT"
            ).count()
            if len(data["members"]) != total_students:
                raise ValidationException(
                    f'All members of this project must belong to the cohort {data["cohort"].name} - {total_students}'
                )

        # the teacher shouldn't be allowed to approve a project that isn't done
        if (
            "project_status" in data
            and "revision_status" in data
            and data["project_status"] == "PENDING"
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException(
                "Only projects that are DONE should be approved", slug="project-marked-approved-when-pending"
            )
        if (
            self.instance.project_status == "PENDING"
            and "revision_status" in data
            and data["revision_status"] == "APPROVED"
        ):
            raise ValidationException(
                "Only projects that are DONE should be approved by the teacher",
                slug="project-marked-approved-when-pending",
            )

        if "revision_status" in data and data["revision_status"] != self.instance.revision_status:
            student_cohorts = CohortUser.objects.filter(
                user__in=self.instance.members.all(), role="STUDENT"
            ).values_list("cohort__id", flat=True)
            student_academies = CohortUser.objects.filter(
                user__in=self.instance.members.all(), role="STUDENT"
            ).values_list("cohort__academy__id", flat=True)

            # the logged in user could be a teacher from the same cohort as the student
            teacher = CohortUser.objects.filter(
                cohort__id__in=student_cohorts,
                role__in=["TEACHER", "ASSISTANT"],
                user__id=self.context["request"].user.id,
            ).first()

            # the logged in user could be a staff member from the same academy that the student belongs
            staff = ProfileAcademy.objects.filter(
                academy__id__in=student_academies, user__id=self.context["request"].user.id
            ).first()

            # task owner should only be able to mark revision status to PENDING
            if data["revision_status"] != "PENDING" and staff is None and teacher is None:
                raise ValidationException(
                    "Only staff members or teachers from the same academy as this student can update the "
                    "revision status",
                    slug="editing-revision-status-but-is-not-teacher-or-assistant",
                )

        return data


class POSTAssignmentTelemetrySerializer(serializers.ModelSerializer):
    telemetry = serializers.JSONField(required=False, allow_null=True)
    engagement_score = serializers.FloatField(required=False, allow_null=True)
    frustration_score = serializers.FloatField(required=False, allow_null=True)
    metrics_algo_version = serializers.FloatField(required=False, allow_null=True)
    metrics = serializers.JSONField(required=False, allow_null=True)
    total_time = serializers.DurationField(required=False, allow_null=True)
    completion_rate = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = AssignmentTelemetry
        exclude = ("user", "asset_slug", "created_at", "updated_at")

    def create(self, validated_data):
        user = self.context.get("user")
        asset_slug = self.context.get("asset_slug")

        if not user:
            raise ValidationException("User is required", slug="user-required")
        if not asset_slug:
            raise ValidationException("Asset slug is required", slug="asset-slug-required")

        # Check if telemetry already exists (upsert behavior)
        telemetry = AssignmentTelemetry.objects.filter(
            asset_slug=asset_slug, user=user
        ).first()

        if telemetry:
            # Update existing telemetry
            for key, value in validated_data.items():
                setattr(telemetry, key, value)
            telemetry.save()
            return telemetry
        else:
            # Create new telemetry
            return AssignmentTelemetry.objects.create(
                user=user, asset_slug=asset_slug, **validated_data
            )


class PUTAssignmentTelemetrySerializer(serializers.ModelSerializer):
    telemetry = serializers.JSONField(required=False, allow_null=True)
    engagement_score = serializers.FloatField(required=False, allow_null=True)
    frustration_score = serializers.FloatField(required=False, allow_null=True)
    metrics_algo_version = serializers.FloatField(required=False, allow_null=True)
    metrics = serializers.JSONField(required=False, allow_null=True)
    total_time = serializers.DurationField(required=False, allow_null=True)
    completion_rate = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = AssignmentTelemetry
        exclude = ("user", "asset_slug", "created_at", "updated_at")
