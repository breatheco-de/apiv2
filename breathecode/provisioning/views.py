import hashlib
from io import StringIO
import json
import os
from django.shortcuts import redirect
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import ProfileAcademy
from breathecode.provisioning.tasks import upload
from breathecode.utils.decorators import has_permission
from breathecode.utils.i18n import translation
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
    def upload(self, lang, file):
        from ..services.google_cloud import Storage

        # files validation below
        if file.content_type != 'text/csv':
            raise ValidationException(
                translation(lang,
                            en='You can upload only files on the following formats: application/csv',
                            es='Solo puedes subir archivos en los siguientes formatos: application/csv',
                            slug='bad-format'))

        content_bytes = file.read()
        content = content_bytes.decode('utf-8')
        hash = hashlib.sha256(content_bytes).hexdigest()

        file.seek(0)

        csvStringIO = StringIO(content)
        df = pd.read_csv(csvStringIO, sep=',')
        df.reset_index()

        format_error = True

        # gitpod
        fields = ['id', 'creditCents', 'effectiveTime', 'kind', 'metadata']
        if (len(df.keys().intersection(fields)) == len(fields) and len(
            {x
             for x in json.loads(df.iloc[0]['metadata'])}.intersection({'userName', 'contextURL'})) == 2):
            format_error = False

        if format_error:
            # codespaces
            fields = [
                'Username', 'Date', 'Product', 'SKU', 'Quantity', 'Unit Type', 'Price Per Unit ($)',
                'Multiplier', 'Owner'
            ]

        if format_error and len(df.keys().intersection(fields)) == len(fields):
            format_error = False

        # Think about uploading correct files and leaving out incorrect ones
        if format_error:
            raise ValidationException(
                translation(
                    lang,
                    en='CSV file from unknown source or the format has changed and this code must be updated',
                    es='Archivo CSV de fuente desconocida o el formato ha cambiado y este código debe ser '
                    'actualizado',
                    slug='csv-from-unknown-source'))

        # upload file section
        storage = Storage()
        cloud_file = storage.file(os.getenv('PROVISIONING_BUCKET', None), hash)
        created = not cloud_file.exists()
        if created:
            cloud_file.upload(file, content_type=file.content_type)

        upload.delay(hash)

        data = {'file_name': hash, 'status': 'PENDING', 'created': created}

        return data

    @has_permission('upload_provisioning_activity')
    def put(self, request, academy_id=None):
        files = request.data.getlist('file')
        lang = get_user_language(request)

        created = []
        updated = []
        errors = {}

        result = {
            'success': [],
            'failure': [],
        }

        for i in range(len(files)):
            file = files[i]

            try:
                data = self.upload(lang, file)
                was_created = data.pop('created')

                serialized = {
                    'pk': data['file_name'],
                    'display_field': 'index',
                    'display_value': i + 1,
                }

                if was_created:
                    created.append(serialized)
                else:
                    updated.append(serialized)
            except ValidationException as e:
                key = (e.status_code, e.detail)
                if key not in errors:
                    errors[key] = []

                errors[key].append({
                    'display_field': 'index',
                    'display_value': i + 1,
                })

        if created:
            result['success'].append({'status_code': 201, 'resources': created})

        if updated:
            result['success'].append({'status_code': 200, 'resources': updated})

        if errors:
            for ((status_code, detail), value) in errors.items():
                result['failure'].append({
                    'status_code': status_code,
                    'detail': detail,
                    'resources': value,
                })

        return Response(result, status=status.HTTP_207_MULTI_STATUS)


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
