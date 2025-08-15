import logging
from datetime import datetime

from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.actions import get_user_language
from breathecode.utils.decorators import has_permission
from breathecode.utils import APIViewExtensions

from .models import Cohort, CohortUser
from .serializers import GetCohortSerializer
from breathecode.authenticate.models import ProfileAcademy, User

logger = logging.getLogger(__name__)


class AdminCohortView(APIView):
    """Admin endpoint to list all cohorts in the database with optional filters."""

    permission_classes = [IsAuthenticated]
    extensions = APIViewExtensions(paginate=True, sort="-kickoff_date")

    @has_permission("read_cohorts_from_all")
    def get(self, request):
        handler = self.extensions(request)
        lang = get_user_language(request)

        items = Cohort.objects.all().select_related(
            "academy", "syllabus_version__syllabus", "schedule"
        )

        # Filter by academy IDs
        academy_ids = request.GET.get("academy_ids")
        if academy_ids:
            try:
                academy_id_list = [int(x.strip()) for x in academy_ids.split(",")]
                items = items.filter(academy__id__in=academy_id_list)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid academy_ids format. Must be comma-separated integers.",
                        es="Formato de academy_ids inválido. Debe ser enteros separados por comas.",
                        slug="invalid-academy-ids-format",
                    )
                )

        # Filter by stage
        stage = request.GET.get("stage")
        if stage:
            items = items.filter(stage__in=stage.upper().split(","))

        # Filter by private
        private = request.GET.get("private")
        if private is not None:
            if private.lower() == "true":
                items = items.filter(private=True)
            elif private.lower() == "false":
                items = items.filter(private=False)

        # Filter by kickoff date
        kickoff_date_gte = request.GET.get("kickoff_date_gte")
        if kickoff_date_gte:
            try:
                date_obj = datetime.fromisoformat(kickoff_date_gte.replace("Z", "+00:00"))
                items = items.filter(kickoff_date__gte=date_obj)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid kickoff_date_gte format. Use ISO format (YYYY-MM-DDTHH:MM:SS).",
                        es="Formato de kickoff_date_gte inválido. Use formato ISO (YYYY-MM-DDTHH:MM:SS).",
                        slug="invalid-kickoff-date-gte-format",
                    )
                )

        kickoff_date_lte = request.GET.get("kickoff_date_lte")
        if kickoff_date_lte:
            try:
                date_obj = datetime.fromisoformat(kickoff_date_lte.replace("Z", "+00:00"))
                items = items.filter(kickoff_date__lte=date_obj)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid kickoff_date_lte format. Use ISO format (YYYY-MM-DDTHH:MM:SS).",
                        es="Formato de kickoff_date_lte inválido. Use formato ISO (YYYY-MM-DDTHH:MM:SS).",
                        slug="invalid-kickoff-date-lte-format",
                    )
                )

        # Filter by ending date
        ending_date_gte = request.GET.get("ending_date_gte")
        if ending_date_gte:
            try:
                date_obj = datetime.fromisoformat(ending_date_gte.replace("Z", "+00:00"))
                items = items.filter(ending_date__gte=date_obj)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid ending_date_gte format. Use ISO format (YYYY-MM-DDTHH:MM:SS).",
                        es="Formato de ending_date_gte inválido. Use formato ISO (YYYY-MM-DDTHH:MM:SS).",
                        slug="invalid-ending-date-gte-format",
                    )
                )

        ending_date_lte = request.GET.get("ending_date_lte")
        if ending_date_lte:
            try:
                date_obj = datetime.fromisoformat(ending_date_lte.replace("Z", "+00:00"))
                items = items.filter(ending_date__lte=date_obj)
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid ending_date_lte format. Use ISO format (YYYY-MM-DDTHH:MM:SS).",
                        es="Formato de ending_date_lte inválido. Use formato ISO (YYYY-MM-DDTHH:MM:SS).",
                        slug="invalid-ending-date-lte-format",
                    )
                )

        # Filter by never_ends
        never_ends = request.GET.get("never_ends")
        if never_ends is not None:
            if never_ends.lower() == "true":
                items = items.filter(never_ends=True)
            elif never_ends.lower() == "false":
                items = items.filter(never_ends=False)

        # Filter by saas (available_as_saas)
        saas = request.GET.get("saas")
        if saas is not None:
            if saas.lower() == "true":
                items = items.filter(available_as_saas=True)
            elif saas.lower() == "false":
                items = items.filter(available_as_saas=False)

        # Filter by language
        language = request.GET.get("language")
        if language:
            items = items.filter(language__in=language.split(","))

        items = handler.queryset(items)
        serializer = GetCohortSerializer(items, many=True)
        return handler.response(serializer.data)


class AdminStudentView(APIView):
    """Admin endpoint to list all students in the database with optional filters."""

    permission_classes = [IsAuthenticated]
    extensions = APIViewExtensions(paginate=True, sort="-date_joined")

    @has_permission("read_students_from_all")
    def get(self, request):
        handler = self.extensions(request)
        lang = get_user_language(request)

        # Get all users who are students (either in cohorts or in ProfileAcademy with student role)
        # We'll use a complex query to avoid duplicates and include all necessary information
        
        # First, get users who are students in cohorts
        cohort_students = CohortUser.objects.filter(
            role="STUDENT"
        ).select_related(
            "user", "cohort", "cohort__academy"
        ).values(
            "user__id", "user__first_name", "user__last_name", "user__email", 
            "user__date_joined", "finantial_status", "educational_status",
            "cohort__id", "cohort__name", "cohort__slug", "cohort__academy__id", 
            "cohort__academy__name", "cohort__academy__slug"
        )
        
        # Get users who are students in ProfileAcademy but may not be in cohorts
        profile_students = ProfileAcademy.objects.filter(
            role__slug="student"
        ).select_related(
            "user", "academy"
        ).values(
            "user__id", "user__first_name", "user__last_name", "user__email",
            "user__date_joined", "academy__id", "academy__name", "academy__slug",
            "first_name", "last_name", "email"  # ProfileAcademy specific fields
        )
        
        # Combine and process the data to avoid duplicates
        students_data = {}
        
        # Process cohort students
        for cs in cohort_students:
            user_id = cs["user__id"]
            if user_id not in students_data:
                students_data[user_id] = {
                    "id": user_id,
                    "first_name": cs["user__first_name"],
                    "last_name": cs["user__last_name"],
                    "email": cs["user__email"],
                    "date_joined": cs["user__date_joined"],
                    "cohorts": [],
                    "profile_academies": [],
                    "finantial_statuses": [],
                    "educational_statuses": []
                }
            
            # Add cohort information
            cohort_info = {
                "id": cs["cohort__id"],
                "name": cs["cohort__name"],
                "slug": cs["cohort__slug"],
                "academy": {
                    "id": cs["cohort__academy__id"],
                    "name": cs["cohort__academy__name"],
                    "slug": cs["cohort__academy__slug"]
                }
            }
            students_data[user_id]["cohorts"].append(cohort_info)
            
            # Add financial and educational statuses
            if cs["finantial_status"]:
                students_data[user_id]["finantial_statuses"].append(cs["finantial_status"])
            if cs["educational_status"]:
                students_data[user_id]["educational_statuses"].append(cs["educational_status"])
        
        # Process profile students
        for ps in profile_students:
            user_id = ps["user__id"]
            if user_id not in students_data:
                # Use ProfileAcademy fields if available, fallback to User fields
                first_name = ps["first_name"] or ps["user__first_name"]
                last_name = ps["last_name"] or ps["user__last_name"]
                email = ps["email"] or ps["user__email"]
                
                students_data[user_id] = {
                    "id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "date_joined": ps["user__date_joined"],
                    "cohorts": [],
                    "profile_academies": [],
                    "finantial_statuses": [],
                    "educational_statuses": []
                }
            else:
                # Update existing student data with ProfileAcademy fields if they're more complete
                if ps["first_name"] and not students_data[user_id]["first_name"]:
                    students_data[user_id]["first_name"] = ps["first_name"]
                if ps["last_name"] and not students_data[user_id]["last_name"]:
                    students_data[user_id]["last_name"] = ps["last_name"]
                if ps["email"] and not students_data[user_id]["email"]:
                    students_data[user_id]["email"] = ps["email"]
            
            # Add profile academy information
            profile_academy_info = {
                "academy": {
                    "id": ps["academy__id"],
                    "name": ps["academy__name"],
                    "slug": ps["academy__slug"]
                }
            }
            students_data[user_id]["profile_academies"].append(profile_academy_info)
        
        # Apply filters
        filtered_students = list(students_data.values())
        
        # Filter by cohort IDs
        cohort_filter = request.GET.get("cohort")
        if cohort_filter:
            try:
                cohort_ids = [int(x.strip()) for x in cohort_filter.split(",")]
                filtered_students = [
                    student for student in filtered_students
                    if any(cohort["id"] in cohort_ids for cohort in student["cohorts"])
                ]
            except ValueError:
                raise ValidationException(
                    translation(
                        lang,
                        en="Invalid cohort format. Must be comma-separated integers.",
                        es="Formato de cohort inválido. Debe ser enteros separados por comas.",
                        slug="invalid-cohort-format",
                    )
                )
        
        # Filter by like (first name, last name, email)
        like_filter = request.GET.get("like")
        if like_filter:
            like_lower = like_filter.lower()
            filtered_students = [
                student for student in filtered_students
                if (like_lower in (student["first_name"] or "").lower() or
                    like_lower in (student["last_name"] or "").lower() or
                    like_lower in (student["email"] or "").lower())
            ]
        
        # Filter by financial status
        finantial_status_filter = request.GET.get("finantial_status")
        if finantial_status_filter:
            statuses = [x.strip().upper() for x in finantial_status_filter.split(",")]
            filtered_students = [
                student for student in filtered_students
                if any(status in student["finantial_statuses"] for status in statuses)
            ]
        
        # Filter by educational status
        educational_status_filter = request.GET.get("educational_status")
        if educational_status_filter:
            statuses = [x.strip().upper() for x in educational_status_filter.split(",")]
            filtered_students = [
                student for student in filtered_students
                if any(status in student["educational_statuses"] for status in statuses)
            ]
        
        # Apply pagination and sorting
        # Since we're working with a list, we need to handle pagination manually
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        
        # Sort by date_joined (newest first by default)
        sort_field = request.GET.get("sort", "-date_joined")
        if sort_field.startswith("-"):
            reverse = True
            sort_field = sort_field[1:]
        else:
            reverse = False
        
        # Sort the filtered students
        if sort_field == "date_joined":
            filtered_students.sort(key=lambda x: x["date_joined"], reverse=reverse)
        elif sort_field == "first_name":
            filtered_students.sort(key=lambda x: x["first_name"] or "", reverse=reverse)
        elif sort_field == "last_name":
            filtered_students.sort(key=lambda x: x["last_name"] or "", reverse=reverse)
        elif sort_field == "email":
            filtered_students.sort(key=lambda x: x["email"] or "", reverse=reverse)
        
        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_students = filtered_students[start_index:end_index]
        
        # Prepare response data
        response_data = {
            "count": len(filtered_students),
            "next": None if end_index >= len(filtered_students) else page + 1,
            "previous": None if page <= 1 else page - 1,
            "results": paginated_students
        }
        
        return Response(response_data) 