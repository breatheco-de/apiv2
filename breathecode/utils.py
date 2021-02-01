import logging, csv
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.views import exception_handler
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
logger = logging.getLogger(__name__)

def localize_query(query, request, matcher=None):

    # not a part of the staff, cannot access all info
    if isinstance(request.user, AnonymousUser):
        return None

    if request.user.is_staff == True:
        return query

    academy_ids = ProfileAcademy.objects.filter(user=request.user).values_list('academy__id',
        flat=True)

    kwargs = {}
    if matcher is None:
        kwargs["academy__id__in"] = academy_ids
    else:
        kwargs[matcher] = academy_ids

    logger.debug(f"Localizing academies: [{','.join([ str(i) for i in academy_ids])}]")
    # only cohorts from that academy
    query = query.filter(**kwargs)

    return query

permissions = (
        ('blog_view', 'can view blog posts and categories'),
        ('blog_edit', 'can edit blog category and post'),
        ("support_view", "can view tickets"),
        ("support_edit", "can edit tickets"),
        ("activity_view", "can view recruiters, applicants, data, posts"),
        ("activity_edit", "can edit data"),
    )

class ValidationException(APIException):
    status_code = 400
    default_detail = 'There is an error in your request'
    default_code = 'client_error'

    def __init__(self, details, code=400):
        self.status_code = code
        self.default_detail = details
        super().__init__(details)

def capable_of(capability=None):        
    def decorator(function):
        def wrapper(*args, **kwargs):

            if isinstance(capability, str) == False:
                raise Exception("Capability must be a string")

            request = None
            try:
                request = args[1]
            except IndexError:
                raise Exception("Missing request information, please apply this decorator to view class methods only")

            academy_id = None
            if "academy_id" not in kwargs and ('Academy' not in request.headers or 'academy' not in request.headers):
                raise PermissionDenied("Missing academy_id parameter expected for the endpoint url or 'Academy' header")
            elif "academy_id" in kwargs:
                academy_id = kwargs['academy_id']
            else:
                if 'Academy' in request.headers:
                    academy_id = request.headers['Academy']
                if 'academy' in request.headers:
                    academy_id = request.headers['academy']

            if not str(academy_id).isdigit():
                raise ValidationException(f"Academy ID needs to be an integer: {str(academy_id)}")

            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied("Invalid user")

            capable = ProfileAcademy.objects.filter(user=request.user.id, academy__id=academy_id, role__capabilities__slug=capability)
            if capable.count() > 0:
                kwargs['academy_id'] = academy_id
                return function(*args, **kwargs)
            
            raise PermissionDenied(f"You (user: {request.user.id}) don't have this capability: {capability} for academy {academy_id}")
        return wrapper
    return decorator

def breathecode_exception_handler(exc, context):
    # This is to be used with the Django REST Framework (DRF) as its
    # global exception handler.  It replaces the POST data of the Django
    # request with the parsed data from the DRF.  This is necessary
    # because we cannot read the request data/stream more than once.
    # This will allow us to see the parsed POST params in the rollbar
    # exception log.

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    context['request']._request.POST = context['request'].data
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.

    if response is not None:
        if isinstance(response.data, list):
            if response.data[0].code != 'invalid':
                response.data = { 'status_code': response.data[0].code, 'details': str(response.data[0]) }
            else:
                response.data = { 'status_code': 500, 'details': str(response.data[0]) }
        else:
            response.data['status_code'] = response.status_code

    return response


class AdminExportCsvMixin:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected as CSV"