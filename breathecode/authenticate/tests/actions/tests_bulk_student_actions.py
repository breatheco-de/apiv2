"""
Unit tests for bulk_student_actions: classify_bulk_student_row, validate_bulk_student_row,
process_bulk_student_row.
"""

from unittest.mock import MagicMock, patch

from capyc.rest_framework.exceptions import ValidationException

from breathecode.authenticate.utils.bulk_student_manager import (
    BulkStudentScenario,
    classify_bulk_student_row,
    process_bulk_student_row,
    validate_bulk_student_row,
)
from breathecode.tests.mixins import GenerateModelsMixin

from ..mixins.new_auth_test_case import AuthTestCase


class ClassifyBulkStudentRowTestSuite(AuthTestCase):
    """Tests for classify_bulk_student_row."""

    def test_classify_new_user(self):
        self.bc.database.create(academy=1, cohort=1)
        scenario = classify_bulk_student_row(academy_id=1, cohort_id=1, email="newuser@example.com")
        self.assertEqual(scenario, BulkStudentScenario.NEW_USER)

    def test_classify_already_in_cohort(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            cohort=1,
            cohort_user=1,
        )
        scenario = classify_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=model.cohort.id,
            email=model.user.email,
        )
        self.assertEqual(scenario, BulkStudentScenario.ALREADY_IN_COHORT)

    def test_classify_same_academy_different_cohort(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            cohort=2,
            profile_academy=1,
        )
        cohort2 = model.cohort
        cohort1 = self.bc.database.create(cohort=1, academy=model.academy).cohort
        scenario = classify_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=cohort1.id,
            email=model.user.email,
        )
        self.assertEqual(scenario, BulkStudentScenario.SAME_ACADEMY_DIFFERENT_COHORT)

    def test_classify_different_academy_no_profile(self):
        model = self.bc.database.create(user=1, academy=1, cohort=1)
        academy2 = self.bc.database.create(academy=1).academy
        cohort2 = self.bc.database.create(cohort=1, academy=academy2).cohort
        scenario = classify_bulk_student_row(
            academy_id=academy2.id,
            cohort_id=cohort2.id,
            email=model.user.email,
        )
        self.assertEqual(scenario, BulkStudentScenario.DIFFERENT_ACADEMY_NO_PROFILE)

    def test_classify_different_academy_has_profile(self):
        user = self.bc.database.create(user=1).user
        academy1 = self.bc.database.create(academy=1).academy
        academy2 = self.bc.database.create(academy=1).academy
        self.bc.database.create(profile_academy=1, user=user, academy=academy1)
        self.bc.database.create(profile_academy=1, user=user, academy=academy2)
        cohort2 = self.bc.database.create(cohort=1, academy=academy2).cohort
        scenario = classify_bulk_student_row(
            academy_id=academy2.id,
            cohort_id=cohort2.id,
            email=user.email,
        )
        self.assertEqual(scenario, BulkStudentScenario.DIFFERENT_ACADEMY_HAS_PROFILE)

    def test_classify_empty_email_raises(self):
        """When email is blank, classify raises ValidationException."""
        self.bc.database.create(academy=1, cohort=1)
        for blank in ("", "   ", None):
            with self.subTest(blank=repr(blank)):
                with self.assertRaises(ValidationException) as cm:
                    classify_bulk_student_row(academy_id=1, cohort_id=1, email=blank or "")
                self.assertEqual(getattr(cm.exception, "slug", None), "email-required")

    def test_classify_cohort_not_found_raises(self):
        """When cohort does not exist or does not belong to academy, classify raises ValidationException."""
        self.bc.database.create(academy=1, cohort=1)
        with self.assertRaises(ValidationException) as cm:
            classify_bulk_student_row(academy_id=1, cohort_id=999, email="any@example.com")
        self.assertEqual(getattr(cm.exception, "slug", None), "cohort-not-found")


class ValidateBulkStudentRowTestSuite(AuthTestCase):
    """Tests for validate_bulk_student_row (soft run)."""

    def test_validate_returns_classification_and_student_fields(self):
        self.bc.database.create(academy=1, cohort=1)
        row = {"email": "a@a.com", "first_name": "A", "last_name": "B", "phone": "123"}
        result = validate_bulk_student_row(academy_id=1, cohort_id=1, row_data=row)
        self.assertEqual(result["email"], "a@a.com")
        self.assertEqual(result["first_name"], "A")
        self.assertEqual(result["last_name"], "B")
        self.assertEqual(result["phone"], "123")
        self.assertIn(result["classification"], (BulkStudentScenario.NEW_USER.value, BulkStudentScenario.NEW_USER))
        self.assertIn(result["status"], ("created", "failed"))

    def test_validate_soft_run_plans_with_existing_user_returns_failed(self):
        """When plans are provided and row is existing user, status is failed with slug."""
        model = self.bc.database.create(
            user=1,
            academy=1,
            cohort=1,
            profile_academy=1,
        )
        cohort2 = self.bc.database.create(cohort=1, academy=model.academy).cohort
        row = {"email": model.user.email, "first_name": "A", "last_name": "B"}
        result = validate_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=cohort2.id,
            row_data=row,
            plans=[1],
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["slug"], "cannot-add-plans-to-existing-user")
        self.assertEqual(result["classification"], BulkStudentScenario.SAME_ACADEMY_DIFFERENT_COHORT.value)

    def test_validate_cohort_not_found_returns_failed(self):
        """When cohort does not exist, validate returns failed with slug cohort-not-found."""
        self.bc.database.create(academy=1, cohort=1)
        row = {"email": "a@a.com", "first_name": "A", "last_name": "B"}
        result = validate_bulk_student_row(academy_id=1, cohort_id=999, row_data=row)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["slug"], "cohort-not-found")
        self.assertEqual(result["classification"], BulkStudentScenario.NEW_USER.value)


class ProcessBulkStudentRowTestSuite(AuthTestCase):
    """Unit tests for process_bulk_student_row (create/skip/fail and DB writes)."""

    def test_process_already_in_cohort_returns_skipped(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            cohort=1,
            cohort_user=1,
        )
        row = {"email": model.user.email, "first_name": "A", "last_name": "B"}
        result = process_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=model.cohort.id,
            row_data=row,
            author_user_id=model.user.id,
        )
        self.assertEqual(result["classification"], BulkStudentScenario.ALREADY_IN_COHORT.value)
        self.assertEqual(result["status"], "skipped")
        self.assertIn("already in this cohort", (result.get("message") or ""))

    def test_process_same_academy_different_cohort_creates_cohort_user(self):
        model = self.bc.database.create(
            user=1,
            academy=1,
            cohort=2,
            profile_academy=1,
        )
        cohort1 = self.bc.database.create(cohort=1, academy=model.academy).cohort
        row = {"email": model.user.email, "first_name": "A", "last_name": "B"}
        result = process_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=cohort1.id,
            row_data=row,
            author_user_id=model.user.id,
        )
        self.assertEqual(result["classification"], BulkStudentScenario.SAME_ACADEMY_DIFFERENT_COHORT.value)
        self.assertEqual(result["status"], "created")
        self.assertIsNotNone(result.get("cohort_user_id"))
        from breathecode.admissions.models import CohortUser

        cu = CohortUser.objects.filter(cohort=cohort1, user=model.user).first()
        self.assertIsNotNone(cu)
        self.assertEqual(cu.id, result["cohort_user_id"])

    def test_process_different_academy_has_profile_creates_cohort_user(self):
        user = self.bc.database.create(user=1).user
        academy1 = self.bc.database.create(academy=1).academy
        academy2 = self.bc.database.create(academy=1).academy
        self.bc.database.create(profile_academy=1, user=user, academy=academy1)
        self.bc.database.create(profile_academy=1, user=user, academy=academy2)
        cohort2 = self.bc.database.create(cohort=1, academy=academy2).cohort
        author = self.bc.database.create(user=1).user
        row = {"email": user.email, "first_name": "A", "last_name": "B"}
        result = process_bulk_student_row(
            academy_id=academy2.id,
            cohort_id=cohort2.id,
            row_data=row,
            author_user_id=author.id,
        )
        self.assertEqual(result["classification"], BulkStudentScenario.DIFFERENT_ACADEMY_HAS_PROFILE.value)
        self.assertEqual(result["status"], "created")
        self.assertIsNotNone(result.get("cohort_user_id"))
        from breathecode.admissions.models import CohortUser

        cu = CohortUser.objects.filter(cohort=cohort2, user=user).first()
        self.assertIsNotNone(cu)

    def test_process_empty_email_returns_failed(self):
        self.bc.database.create(academy=1, cohort=1, user=1)
        row = {"email": "", "first_name": "A", "last_name": "B"}
        result = process_bulk_student_row(
            academy_id=1,
            cohort_id=1,
            row_data=row,
            author_user_id=1,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["slug"], "email-required")

    def test_process_cohort_not_found_returns_failed(self):
        self.bc.database.create(academy=1, cohort=1, user=1)
        row = {"email": "new@example.com", "first_name": "A", "last_name": "B"}
        result = process_bulk_student_row(
            academy_id=1,
            cohort_id=999,
            row_data=row,
            author_user_id=1,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["slug"], "cohort-not-found")

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_process_new_user_creates_profile_academy_and_cohort_user(self):
        model = self.bc.database.create(
            academy=1,
            cohort=1,
            user=1,
            role="student",
        )
        row = {"email": "newuser@example.com", "first_name": "New", "last_name": "User"}
        result = process_bulk_student_row(
            academy_id=model.academy.id,
            cohort_id=model.cohort.id,
            row_data=row,
            author_user_id=model.user.id,
            invite=True,
        )
        self.assertEqual(result["classification"], BulkStudentScenario.NEW_USER.value)
        self.assertEqual(result["status"], "created")
        self.assertIsNotNone(result.get("profile_academy_id"))
        self.assertIsNotNone(result.get("cohort_user_id"))
        from breathecode.authenticate.models import ProfileAcademy
        from breathecode.admissions.models import CohortUser

        pa = ProfileAcademy.objects.filter(email="newuser@example.com", academy=model.academy).first()
        self.assertIsNotNone(pa)
        cu = CohortUser.objects.filter(cohort=model.cohort, user=pa.user).first()
        self.assertIsNotNone(cu)
