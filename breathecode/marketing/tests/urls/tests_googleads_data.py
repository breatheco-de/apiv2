"""
Test /academy/cohort
"""

import urllib, pytz
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins import MarketingTestCase


class AcademyCohortTestSuite(MarketingTestCase):

    def test_googleads_data__without_entries(self):
        """Test /academy/cohort without auth"""

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_bad_gclid(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "532", "deal_status": "WON"}
        model = self.generate_models(academy=True, form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_empty_gclid(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"deal_status": "WON"}
        model = self.generate_models(academy=True, form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_empty_values(self):
        """Test /academy/cohort without auth"""
        model = self.generate_models(academy=True, form_entry=True)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry_bad_deal_status(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "LOST"}
        model = self.generate_models(academy=True, form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        print(model["form_entry"].gclid)
        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entry(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(academy=True, form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        gclid = model["form_entry"].gclid
        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{gclid},,{conversion_time},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model2 = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)

        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        convertion_time2 = model2["form_entry"].created_at.astimezone(timezone)
        conversion_time2 = convertion_time2.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,",
                f"{model2['form_entry'].gclid},,{conversion_time2},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_bad_values(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "123", "deal_status": "LOST"}
        model2 = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model3 = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        response = self.client.get(url)
        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        convertion_time2 = model3["form_entry"].created_at.astimezone(timezone)
        conversion_time2 = convertion_time2.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,",
                f"{model3['form_entry'].gclid},,{conversion_time2},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_with_academy_slug(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model3 = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        args = {"academy_slug": ",".join(list(dict.fromkeys([model.academy.slug])))}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url)

        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_with_academy_id(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model3 = self.generate_models(form_entry=True, form_entry_kwargs=form_entry_kwargs)

        url = reverse_lazy("marketing:googleads_csv")
        args = {"academy": "1"}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url)

        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_with_two_academy_slug(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model2 = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        models = [model, model2]

        url = reverse_lazy("marketing:googleads_csv")
        args = {"academy_slug": ",".join(list(dict.fromkeys([x.academy.slug for x in models])))}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url)

        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        convertion_time2 = model2["form_entry"].created_at.astimezone(timezone)
        conversion_time2 = convertion_time2.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,",
                f"{model2['form_entry'].gclid},,{conversion_time2},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_googleads_data__with_entries_with_two_academy_id(self):
        """Test /academy/cohort without auth"""
        form_entry_kwargs = {"gclid": "D_BwE", "deal_status": "WON"}
        model = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        form_entry_kwargs = {"gclid": "A_BwE", "deal_status": "WON"}
        model2 = self.generate_models(form_entry=True, academy=True, form_entry_kwargs=form_entry_kwargs)

        models = [model, model2]

        url = reverse_lazy("marketing:googleads_csv")
        args = {"academy": "1,2"}
        url = url + "?" + urllib.parse.urlencode(args)
        response = self.client.get(url)

        timezone = pytz.timezone("US/Eastern")
        convertion_time = model["form_entry"].created_at.astimezone(timezone)
        conversion_time = convertion_time.strftime("%Y-%m-%d %H:%M:%S")

        convertion_time2 = model2["form_entry"].created_at.astimezone(timezone)
        conversion_time2 = convertion_time2.strftime("%Y-%m-%d %H:%M:%S")

        expected = "\r\n".join(
            [
                "Parameters:TimeZone=US/Eastern",
                "Google Click ID,Conversion Name,Conversion Time,Conversion Value,Conversion Currency",
                f"{model['form_entry'].gclid},,{conversion_time},,",
                f"{model2['form_entry'].gclid},,{conversion_time2},,\r\n",
            ]
        )

        self.assertEqual(response.content.decode("utf-8"), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
