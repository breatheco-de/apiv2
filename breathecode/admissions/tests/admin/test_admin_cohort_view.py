"""
Test /admin/cohort endpoint
"""

from datetime import datetime, timezone, timedelta
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Cohort
from ..mixins import AdmissionsTestCase


class TestAdminCohortView(AdmissionsTestCase):
    """Test the admin cohort endpoint"""

    def _create_user_with_permission(self):
        """Helper method to create a user with read_cohorts_from_all permission"""
        user = self.bc.database.create(user={'is_superuser': False})
        permission = self.bc.database.create(permission={'codename': 'read_cohorts_from_all'})
        user.user.user_permissions.add(permission.permission)
        return user

    def test_admin_cohort_endpoint_requires_permission(self):
        """Test that the endpoint requires read_cohorts_from_all permission"""
        url = reverse("admissions:admin_cohort")
        
        # Test without authentication
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with regular user (without permission)
        user = self.bc.database.create(user={'is_superuser': False})
        self.client.force_authenticate(user=user.user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_cohort_endpoint_with_permission(self):
        """Test that the endpoint works with read_cohorts_from_all permission"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Test with no cohorts
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_admin_cohort_endpoint_filters_academy_ids(self):
        """Test filtering by academy IDs"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create academies and cohorts
        academy1 = self.bc.database.create(academy=1)
        academy2 = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy1.academy)
        cohort2 = self.bc.database.create(cohort=1, academy=academy2.academy)
        
        # Test filtering by academy ID
        response = self.client.get(f"{url}?academy_ids={academy1.academy.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == cohort1.cohort.id

        # Test filtering by multiple academy IDs
        response = self.client.get(f"{url}?academy_ids={academy1.academy.id},{academy2.academy.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_admin_cohort_endpoint_filters_stage(self):
        """Test filtering by stage"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different stages
        academy = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy.academy, stage="ACTIVE")
        cohort2 = self.bc.database.create(cohort=1, academy=academy.academy, stage="INACTIVE")
        
        # Test filtering by stage
        response = self.client.get(f"{url}?stage=ACTIVE")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["stage"] == "ACTIVE"

        # Test filtering by multiple stages
        response = self.client.get(f"{url}?stage=ACTIVE,INACTIVE")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_admin_cohort_endpoint_filters_private(self):
        """Test filtering by private status"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different private status
        academy = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy.academy, private=True)
        cohort2 = self.bc.database.create(cohort=1, academy=academy.academy, private=False)
        
        # Test filtering by private=True
        response = self.client.get(f"{url}?private=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["private"] is True

        # Test filtering by private=False
        response = self.client.get(f"{url}?private=false")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["private"] is False

    def test_admin_cohort_endpoint_filters_dates(self):
        """Test filtering by date ranges"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different dates
        academy = self.bc.database.create(academy=1)
        now = datetime.now(timezone.utc)
        cohort1 = self.bc.database.create(cohort=1,
            academy=academy.academy, 
            kickoff_date=now - timedelta(days=30)
        )
        cohort2 = self.bc.database.create(cohort=1,
            academy=academy.academy, 
            kickoff_date=now + timedelta(days=30)
        )
        
        # Test filtering by kickoff_date_gte
        date_str = now.strftime("%Y-%m-%dT%H:%M:%S")
        response = self.client.get(f"{url}?kickoff_date_gte={date_str}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == cohort2.cohort.id

    def test_admin_cohort_endpoint_filters_never_ends(self):
        """Test filtering by never_ends status"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different never_ends status
        academy = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy.academy, never_ends=True)
        cohort2 = self.bc.database.create(cohort=1, academy=academy.academy, never_ends=False)
        
        # Test filtering by never_ends=True
        response = self.client.get(f"{url}?never_ends=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["never_ends"] is True

        # Test filtering by never_ends=False
        response = self.client.get(f"{url}?never_ends=false")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["never_ends"] is False

    def test_admin_cohort_endpoint_filters_saas(self):
        """Test filtering by available_as_saas status"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different saas status
        academy = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy.academy, available_as_saas=True)
        cohort2 = self.bc.database.create(cohort=1, academy=academy.academy, available_as_saas=False)
        
        # Test filtering by saas=true
        response = self.client.get(f"{url}?saas=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["available_as_saas"] is True

        # Test filtering by saas=false
        response = self.client.get(f"{url}?saas=false")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["available_as_saas"] is False

    def test_admin_cohort_endpoint_filters_language(self):
        """Test filtering by language"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different languages
        academy = self.bc.database.create(academy=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy.academy, language="en")
        cohort2 = self.bc.database.create(cohort=1, academy=academy.academy, language="es")
        
        # Test filtering by language
        response = self.client.get(f"{url}?language=en")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["language"] == "en"

        response = self.client.get(f"{url}?language=es")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["language"] == "es"

    def test_admin_cohort_endpoint_invalid_academy_ids_format(self):
        """Test error handling for invalid academy_ids format"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Test with invalid academy_ids format
        response = self.client.get(f"{url}?academy_ids=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid-academy-ids-format" in response.data["detail"]

    def test_admin_cohort_endpoint_invalid_date_format(self):
        """Test error handling for invalid date format"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Test with invalid date format
        response = self.client.get(f"{url}?kickoff_date_gte=invalid-date")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid-kickoff-date-gte-format" in response.data["detail"]

    def test_admin_cohort_endpoint_pagination(self):
        """Test that the endpoint supports pagination"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create multiple cohorts
        academy = self.bc.database.create(academy=1)
        for i in range(25):  # Create more than default page size
            self.bc.database.create(cohort=1, academy=academy.academy)
        
        # Test pagination
        response = self.client.get(f"{url}?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 10

        response = self.client.get(f"{url}?limit=10&offset=10")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 10

    def test_admin_cohort_endpoint_sorting(self):
        """Test that the endpoint supports sorting"""
        url = reverse("admissions:admin_cohort")
        
        # Create user with permission and authenticate
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create cohorts with different kickoff dates
        academy = self.bc.database.create(academy=1)
        now = datetime.now(timezone.utc)
        cohort1 = self.bc.database.create(cohort=1,
            academy=academy.academy, 
            kickoff_date=now - timedelta(days=30)
        )
        cohort2 = self.bc.database.create(cohort=1,
            academy=academy.academy, 
            kickoff_date=now + timedelta(days=30)
        )
        
        # Test default sorting (by kickoff_date descending)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        # Should be sorted by kickoff_date descending (newest first)
        assert response.data[0]["id"] == cohort2.cohort.id
        assert response.data[1]["id"] == cohort1.cohort.id 