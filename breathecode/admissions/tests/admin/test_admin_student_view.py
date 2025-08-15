from datetime import datetime, timezone, timedelta
from django.urls import reverse
from rest_framework import status

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import ProfileAcademy, Role
from ..mixins import AdmissionsTestCase


class TestAdminStudentView(AdmissionsTestCase):
    """Test the admin student endpoint"""

    def _create_user_with_permission(self):
        """Helper method to create a user with read_students_from_all permission"""
        user = self.bc.database.create(user={'is_superuser': False})
        permission = self.bc.database.create(permission={'codename': 'read_students_from_all'})
        user.user.user_permissions.add(permission.permission)
        return user

    def test_admin_student_endpoint_requires_permission(self):
        """Test that the endpoint requires read_students_from_all permission"""
        url = reverse("admissions:admin_student")

        # Test without authentication
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test with regular user (without permission)
        user = self.bc.database.create(user={'is_superuser': False})
        self.client.force_authenticate(user=user.user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_student_endpoint_success_with_permission(self):
        """Test successful retrieval with read_students_from_all permission"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        
        # Create ProfileAcademy for student
        profile_academy = self.bc.database.create(profile_academy=1, 
            user=student_user.user, 
            academy=academy.academy, 
            role=role.role
        )
        
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1
        
        student = response.data["results"][0]
        assert student["id"] == student_user.user.id
        assert student["email"] == student_user.user.email
        assert student["first_name"] == student_user.user.first_name
        assert student["last_name"] == student_user.user.last_name
        assert len(student["cohorts"]) == 0
        assert len(student["profile_academies"]) == 1

    def test_admin_student_endpoint_filters_cohort(self):
        """Test filtering by cohort IDs"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        cohort = self.bc.database.create(cohort=1, academy=academy.academy)
        
        # Create CohortUser for student
        cohort_user = self.bc.database.create(cohort_user=1,
            user=student_user.user,
            cohort=cohort.cohort,
            role="STUDENT"
        )
        
        # Test filtering by cohort ID
        response = self.client.get(f"{url}?cohort={cohort.cohort.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by non-existent cohort ID
        response = self.client.get(f"{url}?cohort=999")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_admin_student_endpoint_filters_like(self):
        """Test filtering by like (first name, last name, email)"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        
        # Create ProfileAcademy for student
        profile_academy = self.bc.database.create(profile_academy=1,
            user=student_user.user,
            academy=academy.academy,
            role=role.role
        )
        
        # Update the ProfileAcademy with specific fields
        profile_academy.profile_academy.first_name = "John"
        profile_academy.profile_academy.last_name = "Doe"
        profile_academy.profile_academy.email = "john.doe@example.com"
        profile_academy.profile_academy.save()
        
        # Test filtering by first name
        response = self.client.get(f"{url}?like=John")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by last name
        response = self.client.get(f"{url}?like=Doe")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by email
        response = self.client.get(f"{url}?like=john.doe")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by non-existent text
        response = self.client.get(f"{url}?like=NonExistent")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_admin_student_endpoint_filters_finantial_status(self):
        """Test filtering by financial status"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        cohort = self.bc.database.create(cohort=1, academy=academy.academy)
        
        # Create CohortUser for student with financial status
        cohort_user = self.bc.database.create(cohort_user=1,
            user=student_user.user,
            cohort=cohort.cohort,
            role="STUDENT"
        )
        
        # Update the CohortUser with financial status
        cohort_user.cohort_user.finantial_status = "FULLY_PAID"
        cohort_user.cohort_user.save()
        
        # Test filtering by financial status
        response = self.client.get(f"{url}?finantial_status=FULLY_PAID")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by non-existent financial status
        response = self.client.get(f"{url}?finantial_status=LATE")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_admin_student_endpoint_filters_educational_status(self):
        """Test filtering by educational status"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        cohort = self.bc.database.create(cohort=1, academy=academy.academy)
        
        # Create CohortUser for student with educational status
        cohort_user = self.bc.database.create(cohort_user=1,
            user=student_user.user,
            cohort=cohort.cohort,
            role="STUDENT"
        )
        
        # Update the CohortUser with educational status
        cohort_user.cohort_user.educational_status = "ACTIVE"
        cohort_user.cohort_user.save()
        
        # Test filtering by educational status
        response = self.client.get(f"{url}?educational_status=ACTIVE")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        # Test filtering by non-existent educational status
        response = self.client.get(f"{url}?educational_status=GRADUATED")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_admin_student_endpoint_no_duplicates(self):
        """Test that students are not duplicated when they belong to multiple cohorts"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy1 = self.bc.database.create(academy=1)
        academy2 = self.bc.database.create(academy=2)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        cohort1 = self.bc.database.create(cohort=1, academy=academy1.academy)
        cohort2 = self.bc.database.create(cohort=2, academy=academy2.academy)
        
        # Create CohortUser for student in multiple cohorts
        cohort_users = self.bc.database.create(cohort_user=2,
            user=student_user.user,
            cohort=[cohort1.cohort, cohort2.cohort],
            role="STUDENT"
        )
        
        # Update the CohortUser records with different statuses
        cohort_users.cohort_user[0].finantial_status = "FULLY_PAID"
        cohort_users.cohort_user[0].save()
        cohort_users.cohort_user[1].finantial_status = "UP_TO_DATE"
        cohort_users.cohort_user[1].save()
        
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        student = response.data["results"][0]
        assert len(student["cohorts"]) == 2
        assert len(student["finantial_statuses"]) == 2
        assert "FULLY_PAID" in student["finantial_statuses"]
        assert "UP_TO_DATE" in student["finantial_statuses"]

    def test_admin_student_endpoint_pagination(self):
        """Test pagination functionality"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data - multiple students
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        
        # Create 15 students
        for i in range(15):
            student_user = self.bc.database.create(user=1)
            profile_academy = self.bc.database.create(profile_academy=1,
                user=student_user.user,
                academy=academy.academy,
                role=role.role
            )
        
        # Test first page (default page size is 10)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 15
        assert len(response.data["results"]) == 10
        assert response.data["next"] == 2
        assert response.data["previous"] is None
        
        # Test second page
        response = self.client.get(f"{url}?page=2")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5
        assert response.data["next"] is None
        assert response.data["previous"] == 1

    def test_admin_student_endpoint_sorting(self):
        """Test sorting functionality"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        
        # Create students with different names
        student1 = self.bc.database.create(user=1)
        student2 = self.bc.database.create(user=2)
        student3 = self.bc.database.create(user=3)
        
        # Create ProfileAcademy for each student one by one
        profile_academy1 = self.bc.database.create(profile_academy=1,
            user=student1.user,
            academy=academy.academy,
            role=role.role
        )
        
        # Update the first ProfileAcademy record
        profile_academy1.profile_academy.first_name = "Alice"
        profile_academy1.profile_academy.last_name = "Smith"
        profile_academy1.profile_academy.save()
        
        # Create second ProfileAcademy
        profile_academy2 = self.bc.database.create(profile_academy=1,
            user=student2.user,
            academy=academy.academy,
            role=role.role
        )
        
        # Update the second ProfileAcademy record
        profile_academy2.profile_academy.first_name = "Bob"
        profile_academy2.profile_academy.last_name = "Johnson"
        profile_academy2.profile_academy.save()
        
        # Create third ProfileAcademy
        profile_academy3 = self.bc.database.create(profile_academy=1,
            user=student3.user,
            academy=academy.academy,
            role=role.role
        )
        
        # Update the third ProfileAcademy record
        profile_academy3.profile_academy.first_name = "Charlie"
        profile_academy3.profile_academy.last_name = "Brown"
        profile_academy3.profile_academy.save()
        
        # Test sorting by first name (ascending)
        response = self.client.get(f"{url}?sort=first_name")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["first_name"] == "Alice"
        assert results[1]["first_name"] == "Bob"
        assert results[2]["first_name"] == "Charlie"
        
        # Test sorting by first name (descending)
        response = self.client.get(f"{url}?sort=-first_name")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["first_name"] == "Charlie"
        assert results[1]["first_name"] == "Bob"
        assert results[2]["first_name"] == "Alice"

    def test_admin_student_endpoint_invalid_cohort_format(self):
        """Test error handling for invalid cohort format"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Test with invalid cohort format
        response = self.client.get(f"{url}?cohort=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid-cohort-format" in response.data["detail"]

    def test_admin_student_endpoint_students_without_cohorts(self):
        """Test that students without cohorts are included (only ProfileAcademy)"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academy = self.bc.database.create(academy=1)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        
        # Create only ProfileAcademy (no CohortUser)
        profile_academy = self.bc.database.create(profile_academy=1,
            user=student_user.user,
            academy=academy.academy,
            role=role.role
        )
        
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        student = response.data["results"][0]
        assert len(student["cohorts"]) == 0
        assert len(student["profile_academies"]) == 1
        assert student["profile_academies"][0]["academy"]["id"] == academy.academy.id

    def test_admin_student_endpoint_students_with_both_cohorts_and_profile(self):
        """Test students who have both CohortUser and ProfileAcademy records"""
        url = reverse("admissions:admin_student")
        
        # Create user with permission
        user = self._create_user_with_permission()
        self.client.force_authenticate(user=user.user)
        
        # Create test data
        academies = self.bc.database.create(academy=2)
        role = self.bc.database.create(role={'slug': 'student'})
        student_user = self.bc.database.create(user=1)
        cohort = self.bc.database.create(cohort=1, academy=academies.academy[0])
        
        # Create both CohortUser and ProfileAcademy
        cohort_user = self.bc.database.create(cohort_user=1,
            user=student_user.user,
            cohort=cohort.cohort,
            role="STUDENT"
        )
        profile_academy = self.bc.database.create(profile_academy=1,
            user=student_user.user,
            academy=academies.academy[1],
            role=role.role
        )
        
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        
        student = response.data["results"][0]
        assert len(student["cohorts"]) == 1
        assert len(student["profile_academies"]) == 1
        assert student["cohorts"][0]["academy"]["id"] == academies.academy[0].id
        assert student["profile_academies"][0]["academy"]["id"] == academies.academy[1].id 