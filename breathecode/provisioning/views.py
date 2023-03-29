import re
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Avg
from django.http import HttpResponse
from breathecode.admissions.models import CohortUser, Academy
from breathecode.authenticate.models import ProfileAcademy
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.views import private_view, render_message, set_query_parameter
from rest_framework import serializers
from .serializers import (ContainerMeSmallSerializer, ContainerMeBigSerializer)
from .actions import (
    get_provisioning_vendor, )
from .models import (
    ProvisioningProfile, )
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import status
from breathecode.utils import capable_of, ValidationException, HeaderLimitOffsetPagination, GenerateLookupsMixin
from django.db.models import Q
from django.db.models import QuerySet


@private_view()
def redirect_new_container(request):

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
def redirect_workspaces(request):

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
