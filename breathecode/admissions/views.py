import logging
from django.utils import timezone
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser
from django.contrib.auth.models import User
from .serializers import (
    AcademySerializer, CohortSerializer, CertificateSerializer,
    GetCohortSerializer, UserSerializer, CohortUserSerializer,
    GETCohortUserSerializer, CohortUserPUTSerializer, CohortPUTSerializer,
    CohortUserPOSTSerializer
)
from .models import Academy, CohortUser, Certificate, Cohort, STUDENT, DELETED
from breathecode.authenticate.models import ProfileAcademy
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from breathecode.utils import localize_query
from django.http import QueryDict
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cohorts(request, id=None):

    items = Cohort.objects.all()

    # filter only to the local academy
    items = localize_query(items, request)

    upcoming = request.GET.get('upcoming', None)
    if upcoming == 'true':
        now = timezone.now()
        items = items.filter(kickoff_date__gte=now)

    academy = request.GET.get('academy', None)
    if academy is not None:
        items = items.filter(academy__slug__in=academy.split(","))

    location = request.GET.get('location', None)
    if location is not None:
        items = items.filter(academy__slug__in=location.split(","))

    items = items.order_by('kickoff_date')
    serializer = GetCohortSerializer(items, many=True)
    return Response(serializer.data)

# Create your views here.
class AcademyView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = Academy.objects.all()
        serializer = AcademySerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = AcademySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CohortUserView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = CohortUser.objects.all()

        roles = request.GET.get('roles', None)
        if roles is not None:
            items = items.filter(role__in=roles.split(","))

        finantial_status = request.GET.get('finantial_status', None)
        if finantial_status is not None:
            items = items.filter(finantial_status__in=finantial_status.split(","))

        educational_status = request.GET.get('educational_status', None)
        if educational_status is not None:
            items = items.filter(educational_status__in=educational_status.split(","))

        academy = request.GET.get('academy', None)
        if academy is not None:
            items = items.filter(cohort__academy__slug__in=academy.split(","))

        cohorts = request.GET.get('cohorts', None)
        if cohorts is not None:
            items = items.filter(cohort__slug__in=cohorts.split(","))

        serializer = GETCohortUserSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, cohort_id=None):

        user_id = request.data.get('user')
        if cohort_id is None or user_id is None:
            raise serializers.ValidationError("Missing cohort_id or user_id", code=400)

        if User.objects.filter(id=user_id).count() == 0:
            raise serializers.ValidationError("invalid user_id", code=400)

        cohort = Cohort.objects.filter(id=cohort_id)
        if not cohort:
            raise serializers.ValidationError("invalid cohort_id", code=400)

        cohort = localize_query(cohort, request).first() # only from this academy

        if cohort is None:
            logger.debug(f"Cohort not be found in related academies")
            raise serializers.ValidationError('Specified cohort not be found')

        try:
            cohort_user = CohortUser.objects.create(user_id=user_id, cohort_id=cohort_id)
        except IntegrityError:
            raise serializers.ValidationError('Error saving cohort user')

        serializer = CohortUserSerializer(instance=cohort_user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, cohort_id=None, user_id=None):

        if cohort_id is None or user_id is None:
            raise serializers.ValidationError("Missing user_id or cohort_id", code=400)

        cu = CohortUser.objects.filter(user__id=user_id, cohort__id=cohort_id)
        cu = localize_query(cu, request, "cohort__academy__in").first() # only form this academy

        if cu is None:
            raise serializers.ValidationError('Specified cohort and user could not be found')

        serializer = CohortUserPUTSerializer(cu, data=request.data, context={ "request": request })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, cohort_id=None, user_id=None):

        if cohort_id is None or user_id is None:
            raise serializers.ValidationError("Missing user_id or cohort_id", code=400)

        academy_ids = ProfileAcademy.objects.filter(user=request.user).values_list('academy__id',
            flat=True)

        cu = CohortUser.objects.filter(user__id=user_id,cohort__id=cohort_id,
            cohort__academy__id__in=academy_ids).first()
        if cu is None:
            raise serializers.ValidationError('Specified cohort and user could not be found')

        cu.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CohortView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, cohort_id=None):

        if cohort_id is not None:
            item = None
            if str.isnumeric(cohort_id):
                item = Cohort.objects.filter(id=int(cohort_id)).first()
            else:
                item = Cohort.objects.filter(slug=cohort_id).first()

            if item is None:
                return Response(status=status.HTTP_404_NOT_FOUND)

            serializer = GetCohortSerializer(item, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        items = Cohort.objects.all()
        upcoming = request.GET.get('upcoming', None)
        if upcoming == 'true':
            now = timezone.now()
            items = items.filter(kickoff_date__gte=now)

        academy = request.GET.get('academy', None)
        if academy is not None:
            items = items.filter(academy__slug__in=academy.split(","))

        location = request.GET.get('location', None)
        if location is not None:
            items = items.filter(academy__slug__in=location.split(","))

        serializer = GetCohortSerializer(items, many=True)
        return Response(serializer.data)

    def put(self, request, cohort_id=None):

        if cohort_id is None:
            raise serializers.ValidationError("Missing cohort_id", code=400)

        cohort = Cohort.objects.filter(id=cohort_id)
        cohort = localize_query(cohort, request).first() # only from this academy
        if cohort is None:
            logger.debug(f"Cohort not be found in related academies")
            raise serializers.ValidationError('Specified cohort not be found')
        
        serializer = CohortPUTSerializer(cohort, data=request.data, context={ "request": request })
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, cohort_id=None):
        if cohort_id is None:
            raise serializers.ValidationError("Missing cohort_id", code=400)

        try:
            cohort = Cohort.objects.get(id=cohort_id)
        except Cohort.DoesNotExist:
            raise serializers.ValidationError("Cohort doesn't exist", code=400)

        cohort.stage = DELETED
        cohort.save()

        # STUDENT
        cohort_users = CohortUser.objects.filter(
            role=STUDENT,
            cohort__id=cohort_id
        )

        for cohort_user in cohort_users:
            cohort_user.delete()

        return Response(None, status=status.HTTP_204_NO_CONTENT)

class CertificateView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        items = Certificate.objects.all()
        serializer = CertificateSerializer(items, many=True)
        return Response(serializer.data)
