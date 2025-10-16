"""
Tests for catalog endpoints: timezones, countries, cities
"""

from breathecode.admissions.models import City, Country
from ..mixins import AdmissionsTestCase


class CatalogCountriesTestSuite(AdmissionsTestCase):
    """Test /admissions/catalog/countries"""

    def test_get_countries_empty(self):
        """Test getting countries when none exist"""
        url = "/v1/admissions/catalog/countries"
        response = self.client.get(url)

        json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json, [])

    def test_get_countries_with_data(self):
        """Test getting countries with data"""
        # Create test countries
        country1 = Country.objects.create(code="us", name="United States")
        country2 = Country.objects.create(code="es", name="Spain")

        url = "/v1/admissions/catalog/countries"
        response = self.client.get(url)

        json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        
        # Should be ordered by name
        self.assertEqual(json[0]["id"], "es")
        self.assertEqual(json[0]["code"], "es")
        self.assertEqual(json[0]["name"], "Spain")
        self.assertEqual(json[1]["id"], "us")
        self.assertEqual(json[1]["code"], "us")
        self.assertEqual(json[1]["name"], "United States")


class CatalogCitiesTestSuite(AdmissionsTestCase):
    """Test /admissions/catalog/cities"""

    def test_get_cities_empty(self):
        """Test getting cities when none exist"""
        url = "/v1/admissions/catalog/cities"
        response = self.client.get(url)

        json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json, [])

    def test_get_cities_with_data(self):
        """Test getting cities with data"""
        # Create test country and cities
        country = Country.objects.create(code="us", name="United States")
        city1 = City.objects.create(name="Miami", country=country)
        city2 = City.objects.create(name="Boston", country=country)

        url = "/v1/admissions/catalog/cities"
        response = self.client.get(url)

        json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        
        # Should be ordered by name
        self.assertEqual(json[0]["id"], city2.id)
        self.assertEqual(json[0]["name"], "Boston")
        self.assertEqual(json[0]["country"]["id"], "us")
        self.assertEqual(json[0]["country"]["code"], "us")
        self.assertEqual(json[0]["country"]["name"], "United States")
        
        self.assertEqual(json[1]["id"], city1.id)
        self.assertEqual(json[1]["name"], "Miami")
        self.assertEqual(json[1]["country"]["id"], "us")
        self.assertEqual(json[1]["country"]["code"], "us")
        self.assertEqual(json[1]["country"]["name"], "United States")

