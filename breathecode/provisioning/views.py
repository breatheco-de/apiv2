import hashlib
from io import StringIO
import os
from django.shortcuts import redirect
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import ProfileAcademy
from breathecode.provisioning.tasks import upload
from breathecode.utils.views import private_view, render_message
from .actions import get_provisioning_vendor
from .models import ProvisioningProfile
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException
from rest_framework.parsers import FileUploadParser, MultiPartParser
import pandas as pd


@private_view()
def redirect_new_container(request, token):

    user = token.user
    cohort_id = request.GET.get('cohort', None)
    if cohort_id is None: return render_message(request, f'Please specificy a cohort in the URL')

    url = request.GET.get('repo', None)
    if url is None: return render_message(request, f'Please specificy a repository in the URL')

    cu = CohortUser.objects.filter(user=user, cohort_id=cohort_id).first()
    if cu is None: return render_message(request, f"You don't seem to belong to this cohort {cohort_id}.")

    academy_id = cu.cohort.academy.id
    pa = ProfileAcademy.objects.filter(user=user, academy__id=academy_id).first()
    if pa is None: return render_message(request, f"You don't seem to belong to academy {academy.name}")

    all_profiles = ProvisioningProfile.objects.filter(academy__id=academy_id)
    vendor = None
    try:
        vendor = get_provisioning_vendor(user, pa, cu.cohort)
    except Exception as e:
        return render_message(request, str(e))

    if vendor.name.lower() == 'gitpod':
        return redirect(f'https://gitpod.io/#{url}')
    if vendor.name.lower() == 'codespaces':
        url = url.replace('https://github.com/', '')
        return redirect(f'https://codespaces.new/?repo={url}')

    return render_message(
        request, f"Unknown provisioning vendor: '{vendor.name}', please speak with your program manager.")


@private_view()
def redirect_workspaces(request, token):

    user = token.user
    cohort_id = request.GET.get('cohort', None)
    if cohort_id is None: return render_message(request, f'Please specificy a cohort in the URL')

    url = request.GET.get('repo', None)
    if url is None: return render_message(request, f"Please specificy a repository \"repo\" in the URL")

    cu = CohortUser.objects.filter(user=user, cohort_id=cohort_id).first()
    if cu is None: return render_message(request, f"You don't seem to belong to this cohort {cohort_id}.")

    academy_id = cu.cohort.academy.id
    pa = ProfileAcademy.objects.filter(user=user, academy__id=academy_id).first()
    if pa is None: return render_message(request, f"You don't seem to belong to academy {academy.name}")

    all_profiles = ProvisioningProfile.objects.filter(academy__id=academy_id)
    vendor = None
    try:
        vendor = get_provisioning_vendor(user, pa, cu.cohort)
    except Exception as e:
        return render_message(request, str(e))

    return redirect(vendor.workspaces_url)


class UploadView(APIView):
    """
    put:
        Upload a file to Google Cloud.
    """
    parser_classes = [MultiPartParser, FileUploadParser]

    # permission_classes = [AllowAny]

    # upload was separated because in one moment I think that the serializer
    # not should get many create and update operations together
    def upload(self, file, academy_id):
        from ..services.google_cloud import Storage

        result = {
            'data': [],
            'instance': [],
        }

        if not file:
            raise ValidationException('Missing file in request', code=400)

        # files validation below
        if file.content_type != 'application/csv':
            raise ValidationException('You can upload only files on the following formats: application/csv')

        content_bytes = file.read().decode('utf-8')
        content = content_bytes.decode('utf-8')
        hash = hashlib.sha256(content_bytes).hexdigest()

        csvStringIO = StringIO(content)
        df = pd.read_csv(csvStringIO, sep=',', header=None)
        required_fields = ['first_name', 'last_name', 'email', 'location', 'phone', 'language']

        # Think about uploading correct files and leaving out incorrect ones
        for item in required_fields:
            if item not in df.keys():
                return ValidationException(f'{item} field missing inside of csv')

        data = {'file_name': hash, 'status': 'PENDING'}

        # upload file section
        storage = Storage()
        cloud_file = storage.file(os.getenv('DOWNLOADS_BUCKET', None), hash)
        if not cloud_file.exists():
            cloud_file.upload(file, content_type=file.content_type)

        upload.delay(hash)

        return data

    @capable_of('crud_media')
    def put(self, request, academy_id=None):
        files = request.data.getlist('file')
        result = []
        for file in files:
            upload = self.upload(file, academy_id)
            result.append(upload)
        return Response(result, status=status.HTTP_200_OK)


# class ContainerMeView(APIView):
#     """
#     List all snippets, or create a new snippet.
#     """

#     @capable_of('get_containers')
#     def get(self, request, format=None, container_id=None):

#         containers = ProvisioningContainer.objects.filter(user=request.user)
#         lookup = {}

#         assignment = request.GET.get('assignment', None)
#         if assignment is not None:
#             lookup['task_associated_slug'] = assignment

#         like = request.GET.get('like', None)
#         if like is not None:
#             items = items.filter(display_name__icontains=like)

#         sort_by = '-created_at'
#         if 'sort' in self.request.GET and self.request.GET['sort'] != '':
#             sort_by = self.request.GET.get('sort')

#         items = items.filter(**lookup).order_by(sort_by)

#         page = self.paginate_queryset(items, request)
#         serializer = ContainerMeSmallSerializer(page, many=True)

#         if self.is_paginate(request):
#             return self.get_paginated_response(serializer.data)
#         else:
#             return Response(serializer.data, status=200)

#     @capable_of('create_container')
#     def post(self, request):

#         lang = get_user_language(request)

#         p_profile = ProvisioningProfile.objects.filter(profileacademy__user=request.user, profileacademy__academy__id=academy_id).first()
#         if p_profile is None:
#             raise ValidationException(translation(
#                 en="You don't have a provisioning profile for this academy, we don't know were or how to create the computer you will be using, please contact the academy",
#                 es="No hemos podido encontar un proveedor para aprovisionarte una computadora, por favor contacta tu academia"),
#                 slug='no-provisioning-profile')

#         serializer = ProvisioningContainerSerializer(
#                                         data=request.data,
#                                         context={
#                                             'request': request,
#                                             'academy_id': academy_id
#                                         })
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @capable_of('crud_review')
# def delete(self, request, academy_id=None):
#     # TODO: here i don't add one single delete, because i don't know if it is required
#     lookups = self.generate_lookups(request, many_fields=['id'])
#     # automation_objects

#     if not lookups:
#         raise ValidationException('Missing parameters in the querystring', code=400)

#     items = Review.objects.filter(**lookups, academy__id=academy_id)

#     for item in items:
#         item.status = 'IGNORE'
#         item.save()

#     return Response(None, status=status.HTTP_204_NO_CONTENT)
