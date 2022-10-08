from django.contrib.auth.models import AnonymousUser
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q

from breathecode.payments.models import Invoice, ServiceInvoiceItem

from ..validation_exception import ValidationException
from ..exceptions import ProgramingError
from breathecode.authenticate.models import Permission, User

__all__ = ['payment_required']


def consume_service(user: User, service: str) -> bool:
    now = timezone.now()
    invoice = Invoice.objects.filter(Q(valid_until__lte=now) | Q(valid_until=None),
                                     services__service__slug=service,
                                     user=user).exclude(services__how_many=0).first()

    if not invoice:
        return False

    invoice_service = invoice.services.filter(service__slug=service).exclude(how_many=0).first()
    if invoice_service.how_many == -1:
        return True

    invoice_service.how_many -= 1
    invoice_service.save()

    return True


def payment_required(service: str):
    """This decorator check if the current user can access to the resource through of permissions"""

    def decorator(function):

        def wrapper(*args, **kwargs):
            if isinstance(service, str) == False:
                raise ProgramingError('Permission must be a string')

            try:
                if hasattr(args[0], '__class__') and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], 'user') and hasattr(args[0].user, 'has_perm'):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgramingError('Missing request information, use this decorator with DRF View')

            if consume_service(request.user, service):
                return function(*args, **kwargs)

            elif isinstance(request.user, AnonymousUser):
                raise ValidationException(f'Anonymous user don\'t have access to this element: {service}',
                                          code=403,
                                          slug='anonymous-user-without-permission')

            else:
                raise ValidationException((f'You (user: {request.user.id}) don\'t have access to this '
                                           f'element: {service}'),
                                          code=402,
                                          slug='payment-required')

        return wrapper

    return decorator
