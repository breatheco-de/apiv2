"""
Test /cohort
"""

import random
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.admissions.caches import CohortCache
from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from breathecode.utils.datetime_integer import DatetimeInteger

from ..mixins import AdmissionsTestCase


def put_serializer(academy, country, city, data={}):
    """Helper to generate expected response matching GetBigAcademySerializer format."""
    return {
        "id": academy.id,
        "slug": academy.slug,
        "name": academy.name,
        "country": {
            "id": country.code,
            "code": country.code,
            "name": country.name,
        } if country else None,
        "city": {
            "id": city.id,
            "name": city.name,
            "country": {
                "id": country.code,
                "code": country.code,
                "name": country.name,
            } if country else None,
        } if city else None,
        "logo_url": academy.logo_url,
        "icon_url": academy.icon_url,
        "active_campaign_slug": academy.active_campaign_slug,
        "logistical_information": academy.logistical_information,
        "latitude": str(academy.latitude) if academy.latitude else None,
        "longitude": str(academy.longitude) if academy.longitude else None,
        "marketing_email": academy.marketing_email,
        "street_address": academy.street_address,
        "website_url": academy.website_url,
        "marketing_phone": academy.marketing_phone,
        "twitter_handle": academy.twitter_handle,
        "facebook_handle": academy.facebook_handle,
        "instagram_handle": academy.instagram_handle,
        "github_handle": academy.github_handle,
        "linkedin_url": academy.linkedin_url,
        "youtube_url": academy.youtube_url,
        "is_hidden_on_prework": academy.is_hidden_on_prework,
        "white_label_features": academy.get_white_label_features(),
        "owner": {
            "id": academy.owner.id,
            "email": academy.owner.email,
        } if academy.owner else None,
    }


class AcademyCohortIdTestSuite(AdmissionsTestCase):
    """Test /cohort"""

    cache = CohortCache()
    """
    🔽🔽🔽 Auth
    """

    def test__without_auth(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        response = self.client.put(url, {}, format="json")
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "Authentication credentials were not provided.", "status_code": status.HTTP_401_UNAUTHORIZED},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put__without_capability(self):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        self.generate_models(authenticate=True)
        data = {}
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(
            json,
            {"detail": "You (user: 1) don't have this capability: crud_my_academy for academy 1", "status_code": 403},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 Put without required fields
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__without_required_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            syllabus=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        data = {}
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {
            "name": ["This field is required."],
            "slug": ["This field is required."],
            "street_address": ["This field is required."],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                self.bc.format.to_dict(model.academy),
            ],
        )
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, try to modify slug
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__try_to_modify_slug(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            syllabus=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        data = {
            "name": self.bc.fake.name(),
            "slug": self.bc.fake.slug(),
            "street_address": self.bc.fake.address(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = {"detail": "Academy slug cannot be updated", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                self.bc.format.to_dict(model.academy),
            ],
        )
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, passing all the fields
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__passing_all_the_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=3,
            city=3,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            syllabus=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        country = random.choice(model.country)
        city = random.choice(model.city)
        data = {
            "name": self.bc.fake.name(),
            "slug": model.academy.slug,
            "street_address": self.bc.fake.address(),
            "country": country.code,
            "city": city.id,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = put_serializer(model.academy, country, city, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ["country", "city"]
        for field in fields:
            data[f"{field}_id"] = data.pop(field)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                {
                    **self.bc.format.to_dict(model.academy),
                    **data,
                }
            ],
        )
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, with partial update (only updating city)
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__partial_update_only_city(self):
        """Test /academy/me with partial update - only city field"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=2,
            city=2,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        original_name = model.academy.name
        original_street = model.academy.street_address
        new_city = model.city[1]  # Use a different city

        data = {
            "city": new_city.id,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that only city was updated
        updated_academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(updated_academy.city_id, new_city.id)
        self.assertEqual(updated_academy.name, original_name)  # Name unchanged
        self.assertEqual(updated_academy.street_address, original_street)  # Street unchanged
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, without name field (should work - field is optional)
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__without_name_field(self):
        """Test /academy/me without name field - should succeed as name is optional"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=2,
            city=2,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        original_name = model.academy.name
        new_city = model.city[1]

        data = {
            "city": new_city.id,
            "street_address": self.bc.fake.address(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify name was not changed
        updated_academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(updated_academy.name, original_name)
        self.assertEqual(updated_academy.city_id, new_city.id)
        self.assertEqual(updated_academy.street_address, data["street_address"])
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, without street_address field (should work - field is optional)
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__without_street_address_field(self):
        """Test /academy/me without street_address field - should succeed as it's optional"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=2,
            city=2,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        original_street = model.academy.street_address
        new_city = model.city[1]

        data = {
            "name": self.bc.fake.name(),
            "city": new_city.id,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify street_address was not changed
        updated_academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(updated_academy.street_address, original_street)
        self.assertEqual(updated_academy.name, data["name"])
        self.assertEqual(updated_academy.city_id, new_city.id)
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, trying to update slug (should be ignored/rejected)
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__slug_cannot_be_updated(self):
        """Test /academy/me - slug field should not be updateable"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=1,
            city=1,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        original_slug = model.academy.slug

        data = {
            "slug": "new-different-slug",
            "name": self.bc.fake.name(),
        }
        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify slug was NOT changed (it should be ignored/read-only)
        updated_academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(updated_academy.slug, original_slug)  # Slug unchanged
        self.assertEqual(updated_academy.name, data["name"])  # Name changed
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, passing all the wrong fields
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__passing_all_the_wrong_fields(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=3,
            city=3,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            syllabus=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        country = random.choice(model.country)
        city = random.choice(model.city)
        data = {
            "name": self.bc.fake.name(),
            "slug": model.academy.slug,
            "street_address": self.bc.fake.address(),
            "country": country.code,
            "city": city.id,
        }

        incorrect_values = {
            "logo_url": self.bc.fake.url(),
            "icon_url": self.bc.fake.url(),
            "website_url": self.bc.fake.url(),
            "marketing_email": self.bc.fake.email(),
            "feedback_email": self.bc.fake.email(),
            "marketing_phone": self.bc.fake.phone_number(),
            "twitter_handle": self.bc.fake.user_name(),
            "facebook_handle": self.bc.fake.user_name(),
            "instagram_handle": self.bc.fake.user_name(),
            "github_handle": self.bc.fake.user_name(),
            "linkedin_url": self.bc.fake.url(),
            "youtube_url": self.bc.fake.url(),
            "latitude": random.random() * 90 * random.choice([1, -1]),  #
            "longitude": random.random() * 90 * random.choice([1, -1]),
            "zip_code": str(random.randint(1, 1000)),
            "white_labeled": bool(random.randint(0, 1)),
            "active_campaign_slug": self.bc.fake.slug(),
            "available_as_saas": bool(random.randint(0, 1)),
            "status": random.choice(["INACTIVE", "ACTIVE", "DELETED"]),
            "timezone": self.bc.fake.name(),
            "logistical_information": self.bc.fake.text()[:150],
        }

        to_send = data.copy()
        to_send |= incorrect_values

        response = self.client.put(url, to_send, format="json")
        json = response.json()
        expected = put_serializer(model.academy, country, city, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ["country", "city"]
        for field in fields:
            data[f"{field}_id"] = data.pop(field)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                {
                    **self.bc.format.to_dict(model.academy),
                    **data,
                }
            ],
        )
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, passing all the fields
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    def test__put__with_academy__passing_all_the_status(self):
        """Test /cohort/:id without auth"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            country=3,
            city=3,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            syllabus=True,
        )

        # reset because this call are coming from mixer
        cohort_saved.send_robust.call_args_list = []

        country = random.choice(model.country)
        city = random.choice(model.city)
        data = {
            "name": self.bc.fake.name(),
            "slug": model.academy.slug,
            "street_address": self.bc.fake.address(),
            "country": country.code,
            "city": city.id,
        }
        response = self.client.put(url, data, format="json")
        json = response.json()
        expected = put_serializer(model.academy, country, city, data=data)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fields = ["country", "city"]
        for field in fields:
            data[f"{field}_id"] = data.pop(field)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                {
                    **self.bc.format.to_dict(model.academy),
                    **data,
                }
            ],
        )
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, updating logo_url with valid URL
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    @patch("breathecode.utils.url_validator.test_url", MagicMock())
    def test__put__with_academy__update_logo_url_valid(self):
        """Test updating logo_url with a valid URL"""
        from breathecode.admissions.signals import cohort_saved
        from breathecode.utils import url_validator

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # Reset because calls are coming from setup
        cohort_saved.send_robust.call_args_list = []

        new_logo_url = "https://example.com/new-logo.png"
        data = {"logo_url": new_logo_url}

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["logo_url"], new_logo_url)

        # Verify test_url was called to validate the URL
        url_validator.test_url.assert_called_once_with(new_logo_url, allow_relative=False, allow_hash=False)

        # Verify database was updated
        academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(academy.logo_url, new_logo_url)
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, updating logo_url with invalid URL
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    @patch("breathecode.utils.url_validator.test_url", MagicMock(side_effect=Exception("Invalid URL")))
    def test__put__with_academy__update_logo_url_invalid(self):
        """Test updating logo_url with an invalid URL"""
        from breathecode.admissions.signals import cohort_saved

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
        )

        # Reset because calls are coming from setup
        cohort_saved.send_robust.call_args_list = []

        invalid_logo_url = "not-a-valid-url"
        data = {"logo_url": invalid_logo_url}

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid logo URL", json["detail"])
        self.assertEqual(json["slug"], "invalid-logo-url")

        # Verify database was NOT updated
        academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(academy.logo_url, model.academy.logo_url)
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, partial update including logo_url
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    @patch("breathecode.utils.url_validator.test_url", MagicMock())
    def test__put__with_academy__partial_update_with_logo_url(self):
        """Test partial update including logo_url along with other fields"""
        from breathecode.admissions.signals import cohort_saved
        from breathecode.utils import url_validator

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            country=True,
        )

        # Reset because calls are coming from setup
        cohort_saved.send_robust.call_args_list = []

        new_logo_url = "https://example.com/updated-logo.png"
        new_name = "Updated Academy Name"
        data = {"logo_url": new_logo_url, "name": new_name}

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["logo_url"], new_logo_url)
        self.assertEqual(json["name"], new_name)

        # Verify test_url was called to validate the URL
        url_validator.test_url.assert_called_once_with(new_logo_url, allow_relative=False, allow_hash=False)

        # Verify database was updated
        academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(academy.logo_url, new_logo_url)
        self.assertEqual(academy.name, new_name)
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])

    """
    🔽🔽🔽 Put with Academy, partial update including icon_url
    """

    @patch("breathecode.admissions.signals.cohort_saved.send_robust", MagicMock())
    @patch("breathecode.utils.url_validator.test_url", MagicMock())
    def test__put__with_academy__partial_update_with_icon_url(self):
        """Test partial update including icon_url along with other fields"""
        from breathecode.admissions.signals import cohort_saved
        from breathecode.utils import url_validator

        self.headers(academy=1)
        url = reverse_lazy("admissions:academy_me")
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_my_academy",
            role="potato",
            skip_cohort=True,
            country=True,
        )

        # Reset because calls are coming from setup
        cohort_saved.send_robust.call_args_list = []

        new_icon_url = "https://example.com/updated-icon.png"
        new_name = "Updated Academy Name"
        data = {"icon_url": new_icon_url, "name": new_name}

        response = self.client.put(url, data, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["icon_url"], new_icon_url)
        self.assertEqual(json["name"], new_name)

        # Verify test_url was called to validate the URL
        url_validator.test_url.assert_called_once_with(new_icon_url, allow_relative=False, allow_hash=False)

        # Verify database was updated
        academy = self.bc.database.get("admissions.Academy", 1, dict=False)
        self.assertEqual(academy.icon_url, new_icon_url)
        self.assertEqual(academy.name, new_name)
        self.assertEqual(cohort_saved.send_robust.call_args_list, [])
