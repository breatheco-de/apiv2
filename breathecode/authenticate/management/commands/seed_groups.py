from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from breathecode.mentorship.models import MentorProfile
from breathecode.authenticate.models import ProfileAcademy


class Command(BaseCommand):
    help = "Create default system capabilities"

    def handle(self, *args, **options):
        student = Group.objects.filter(name="Student").first()
        teacher = Group.objects.filter(name="Teacher").first()
        teacher_influencer = Group.objects.filter(name="Teacher Influencer").first()
        default = Group.objects.filter(name="Default").first()
        mentor = Group.objects.filter(name="Mentor").first()

        if not default:
            default = Group(name="Default")
            default.save()

        if not mentor:
            mentor = Group(name="Mentor")
            mentor.save()

        if not student:
            student = Group(name="Student")
            student.save()

        if not teacher:
            teacher = Group(name="Teacher")
            teacher.save()

        if not teacher_influencer:
            teacher_influencer = Group(name="Teacher Influencer")
            teacher_influencer.save()

        users = User.objects.filter()
        default.user_set.set(users)

        mentor_ids = MentorProfile.objects.filter().values_list("user__id", flat=True)
        mentors = User.objects.filter(id__in=mentor_ids)
        mentor.user_set.set(mentors)

        profile_ids = ProfileAcademy.objects.filter(user__isnull=False, role__slug="student").values_list(
            "user__id", flat=True
        )
        students = User.objects.filter(id__in=profile_ids)
        student.user_set.set(students)

        profile_ids = ProfileAcademy.objects.filter(user__isnull=False, role__slug="teacher").values_list(
            "user__id", flat=True
        )
        teachers = User.objects.filter(id__in=profile_ids)
        teacher.user_set.set(teachers)

        profile_ids = ProfileAcademy.objects.filter(user__isnull=False, role__slug="teacher_influencer").values_list(
            "user__id", flat=True
        )
        teacher_influencers = User.objects.filter(id__in=profile_ids)
        teacher_influencer.user_set.set(teacher_influencers)
