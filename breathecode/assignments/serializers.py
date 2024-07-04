import logging
import os

from django.contrib.auth.models import User
from rest_framework import serializers

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import ProfileAcademy, Token
from breathecode.utils import serpy
from capyc.rest_framework.exceptions import ValidationException

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
    delivered_at = serpy.Field()
    assignment_telemetry = serpy.MethodField()

    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_assignment_telemetry(self, obj):
        telemetry = AssignmentTelemetry.objects.filter(user=obj.user, asset_slug=obj.associated_slug).first()
        if telemetry is not None:
            return telemetry.telemetry
        return None


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
        token, created = Token.get_or_create(obj.user, token_type="temporal")
        return os.getenv("API_URL") + f"/v1/assignment/task/{str(obj.id)}/deliver/{token}"


class PostTaskSerializer(serializers.ModelSerializer):
    task_status = serializers.CharField(read_only=True)
    revision_status = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        exclude = ("user",)

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

    class Meta:
        model = Task
        exclude = ("user",)

    def validate(self, data):

        if self.instance.user.id != self.context["request"].user.id:
            if "task_status" in data and data["task_status"] != self.instance.task_status:
                raise ValidationException(
                    f"Only the task {self.instance.id} owner can modify its status",
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

        if "task_status" in validated_data and validated_data["task_status"] != instance.task_status:
            tasks_activity.add_activity.delay(
                self.context["request"].user.id,
                "assignment_status_updated",
                related_type="assignments.Task",
                related_id=instance.id,
            )

        return super().update(instance, validated_data)


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
