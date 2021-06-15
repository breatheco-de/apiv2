"""
Test /academy/cohort
"""
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import MarketingTestCase

class AcademyCohortTestSuite(MarketingTestCase):
    def test_googleads_data__without_entries(self):
        """Test /academy/cohort without auth"""

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)

        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time\r\n'
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_bad_gclid(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {'gclid': '532', 'deal_status': 'WON'}
        model = self.generate_models(academy=True, form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)
        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time\r\n'
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_bad_deal_status(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {'gclid': 'D_BwE', 'deal_status': 'LOST'}
        model = self.generate_models(academy=True, form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)
        print(model['form_entry'].gclid)
        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time\r\n'
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {'gclid': 'D_BwE', 'deal_status': 'WON'}
        model = self.generate_models(academy=True, form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)
        gclid = model['form_entry'].gclid
        conversion_time = model['form_entry'].created_at.strftime("%Y-%m-%d %H-%M-%S%z")

        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time',
            f"{gclid},,{conversion_time}\r\n"
        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {'gclid': 'D_BwE', 'deal_status': 'WON'}
        model = self.generate_models(form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {'gclid': 'A_BwE', 'deal_status': 'WON'}
        model2 = self.generate_models(form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)
        conversion_time = model['form_entry'].created_at.strftime("%Y-%m-%d %H-%M-%S%z")
        conversion_time2 = model2['form_entry'].created_at.strftime("%Y-%m-%d %H-%M-%S%z")

        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time',
            f"{model['form_entry'].gclid},,{conversion_time}",
            f"{model2['form_entry'].gclid},,{conversion_time2}\r\n"

        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_bad_values(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {'gclid': 'D_BwE', 'deal_status': 'WON'}
        model = self.generate_models(form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {'gclid': '123', 'deal_status': 'LOST'}
        model2 = self.generate_models(form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {'gclid': 'A_BwE', 'deal_status': 'WON'}
        model3 = self.generate_models(form_entry=True,
            form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy('marketing:googleads_csv')
        response = self.client.get(url)
        conversion_time = model['form_entry'].created_at.strftime("%Y-%m-%d %H-%M-%S%z")
        conversion_time2 = model3['form_entry'].created_at.strftime("%Y-%m-%d %H-%M-%S%z")

        expected = '\r\n'.join([
            'Google Click ID,Conversion Name,Conversion Time',
            f"{model['form_entry'].gclid},,{conversion_time}",
            f"{model3['form_entry'].gclid},,{conversion_time2}\r\n"

        ])

        self.assertEqual(response.content.decode('utf-8'), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)