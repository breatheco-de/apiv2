"""
Test cases for /academy/:id/member/:id
"""
import os
from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status
from django.utils import timezone
from ..mixins import ProvisioningTestCase

UTC_NOW = timezone.now()


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_successfully(provisioning_bill=None,
                        token=None,
                        academy=None,
                        provisioning_activities=[],
                        data={}):
    request = None
    APP_URL = os.getenv('APP_URL', '')

    template = loader.get_template('provisioning_invoice.html')
    status_map = {
        'DUE': 'Due',
        'DISPUTED': 'Disputed',
        'IGNORED': 'Ignored',
        'PENDING': 'Pending',
        'PAID': 'Paid',
        'ERROR': 'Error'
    }

    total_price = 0
    for bill in []:
        total_price += bill['total_price']

    status = data.get('status', 'DUE')

    data = {
        'API_URL': None,
        'COMPANY_NAME': '',
        'COMPANY_CONTACT_URL': '',
        'COMPANY_LEGAL_NAME': '',
        'COMPANY_ADDRESS': '',
        'style__success': '#99ccff',
        'style__danger': '#ffcccc',
        'style__secondary': '#ededed',
        'status': status,
        'token': token.key,
        'title': f'Payments {status_map[status]}',
        'possible_status': [(key, status_map[key]) for key in status_map],
        'bills': provisioning_bill,
        'total_price': total_price,
        **data,
        'bill': provisioning_bill,
        'activities': provisioning_activities,
        'status': status_map['DUE'],
        'title': academy.name,
    }

    return template.render(data)


def render(message):
    request = None
    return loader.render_to_string(
        'message.html',
        {
            'MESSAGE': message,
            'BUTTON': None,
            'BUTTON_TARGET': '_blank',
            'LINK': None
        },
        request,
        using=None,
    )


class AuthenticateTestSuite(ProvisioningTestCase):
    # When: no auth
    # Then: return 302
    def test_without_auth(self):
        url = reverse_lazy('provisioning:bill_id_html', kwargs={'id': 1})
        response = self.client.get(url)

        hash = self.bc.format.to_base64('/v1/provisioning/bill/1/html')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={hash}')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    # When: no profile academies
    # Then: return 403
    def test_403(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('provisioning:bill_id_html', kwargs={'id': 1}) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render('no-access')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.bc.database.list_of('authenticate.ProfileAcademy'), [])

    # When: 1 bill and 2 activities
    # Then: return 200
    def test_2_activities(self):
        model = self.bc.database.create(user=1,
                                        token=1,
                                        provisioning_bill=1,
                                        provisioning_activity=2,
                                        profile_academy=1,
                                        academy=1,
                                        role=1,
                                        capability='crud_provisioning_bill')

        querystring = self.bc.format.to_querystring({'token': model.token.key})
        url = reverse_lazy('provisioning:bill_id_html', kwargs={'id': 1}) + f'?{querystring}'
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_successfully(provisioning_bill=model.provisioning_bill,
                                       token=model.token,
                                       academy=model.academy,
                                       provisioning_activities=model.provisioning_activity,
                                       data={})
        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('provisioning.ProvisioningBill'), [
            self.bc.format.to_dict(model.provisioning_bill),
        ])
