import serpy, logging
from rest_framework import serializers
from .models import Task
from rest_framework.exceptions import ValidationError
from breathecode.utils import ValidationException
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class UserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class TaskGETSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    title = serpy.Field()
    task_status = serpy.Field()
    associated_slug = serpy.Field()
    revision_status = serpy.Field()
    github_url = serpy.Field()
    live_url = serpy.Field()
    task_type = serpy.Field()
    user = UserSmallSerializer()


class PostTaskSerializer(serializers.ModelSerializer):
    task_status = serializers.CharField(read_only=True)
    revision_status = serializers.CharField(read_only=True)

    class Meta:
        model = Task
        exclude = ('user', )

    def validate(self, data):

        user = User.objects.filter(id=self.context["user_id"]).first()
        if user is None:
            raise ValidationException("User does not exists")

        return super(PostTaskSerializer, self).validate({**data, "user": user})

    def create(self, validated_data):

        return Task.objects.create(**validated_data)


# class PostBulkTaskSerializer(serializers.ListSerializer):

#     def validate(self, data):
#         _data = data
#         user = User.objects.filter(id=self.context["user_id"]).first()
#         if user is None:
#             raise ValidationException("User does not exists")
#         logger.debug("User found")

#         for task in _data:
#             PostTaskSerializer.validate({ **task, "user": user })
#         return _data

#     def create(self, validated_data):

#         user = User.objects.filter(id=self.context["user_id"]).first()

#         _tasks = []
#         logger.debug("multiple", validated_data)
#         for task in validated_data:
#             p = { **task, "user_id": user.id }
#             _tasks.append(Task.objects.create(**p))
#         return _tasks


class PUTTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ('user', 'task_type')

    def validate(self, data):

        user = self.context['request'].user
        # the user cannot vote to the same entity within 5 minutes
        # answer = Task.objects.filter(user=self.context['request'].user,id=self.context['answer']).first()
        if self.instance.user.id != self.context['request'].user.id:
            if "task_status" in data and data[
                    "task_status"] != self.instance.task_status:
                raise ValidationException(
                    'Only the task owner can modify its status')
            if "live_url" in data and data[
                    "live_url"] != self.instance.live_url:
                raise ValidationException(
                    'Only the task owner can modify its live_url')
            if "github_url" in data and data[
                    "github_url"] != self.instance.github_url:
                raise ValidationException(
                    'Only the task owner can modify its github_url')

        if "revision_status" in data and data[
                "revision_status"] != self.instance.revision_status:
            student_cohorts = CohortUser.objects.filter(
                user__id=self.instance.user.id,
                role="STUDENT").values_list('cohort__id', flat=True)
            student_academies = CohortUser.objects.filter(
                user__id=self.instance.user.id,
                role="STUDENT").values_list('cohort__academy__id', flat=True)

            # the logged in user could be a teacher from the same cohort as the student
            teacher = CohortUser.objects.filter(
                cohort__id__in=student_cohorts,
                role__in=["TEACHER", "ASSISTANT"],
                user__id=self.context['request'].user.id).first()

            # the logged in user could be a staff member from the same academy that the student belongs
            staff = ProfileAcademy.objects.filter(
                academy__id__in=student_academies,
                user__id=self.context['request'].user.id).first()

            if staff is None and teacher is None:
                raise ValidationException(
                    'Only staff members or teachers from the same academy as this student can update the review status'
                )

        return data
