"""
Test /academy/cohort
"""
from unittest.mock import patch
from mixer.backend.django import mixer
# from random import randint
from breathecode.tests.mocks import (
    GOOGLE_CLOUD_PATH,
    apply_google_cloud_client_mock,
    apply_google_cloud_bucket_mock,
    apply_google_cloud_blob_mock,
)
from ...mixins import AdmissionsTestCase
from ....management.commands.delete_duplicates import Command
# from ...utils import GenerateModels


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""
    @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    def test_delete_duplicates(self):
        """Test /academy/cohort without auth"""
        self.generate_models(cohort=True, user=True)
        models = [
            mixer.blend('admissions.CohortUser',
                        user=self.user,
                        cohort=self.cohort) for _ in range(0, 10)
        ]
        model_dict = self.remove_dinamics_fields(models[0].__dict__)
        command = Command()

        self.assertEqual(command.handle(), None)
        self.assertEqual(self.count_cohort_user(), 1)
        self.assertEqual(self.all_cohort_user_dict(), [model_dict])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_delete_duplicates_with_one_student_graduated(self):
    #     """Test /academy/cohort without auth"""
    #     self.generate_models(cohort=True, user=True)

    #     rand_start = randint(0, 9)
    #     rand_end = randint(0, 9)

    #     models = (
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort) for _ in
    #             range(0, rand_start)] +
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort,
    #             educational_status='GRADUATED')] +
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort) for _ in
    #             range(0, rand_end)]
    #     )
    #     model_dict = self.remove_dinamics_fields(models[rand_start].__dict__)
    #     command = Command()

    #     self.assertEqual(command.cohort_users(), None)
    #     self.assertEqual(self.count_cohort_user(), 1)
    #     self.assertEqual(self.all_cohort_user_dict(), [model_dict])

    # @patch(GOOGLE_CLOUD_PATH['client'], apply_google_cloud_client_mock())
    # @patch(GOOGLE_CLOUD_PATH['bucket'], apply_google_cloud_bucket_mock())
    # @patch(GOOGLE_CLOUD_PATH['blob'], apply_google_cloud_blob_mock())
    # def test_delete_duplicates_with_one_student_with_finantial_status(self):
    #     """Test /academy/cohort without auth"""
    #     self.generate_models(cohort=True, user=True)

    #     rand_start = randint(0, 9)
    #     rand_end = randint(0, 9)

    #     models = (
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort) for _ in
    #             range(0, rand_start)] +
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort,
    #             finantial_status='LATE')] +
    #         [mixer.blend('admissions.CohortUser', user=self.user, cohort=self.cohort) for _ in
    #             range(0, rand_end)]
    #     )
    #     model_dict = self.remove_dinamics_fields(models[rand_start].__dict__)
    #     command = Command()

    #     self.assertEqual(command.cohort_users(), None)
    #     self.assertEqual(self.count_cohort_user(), 1)
    #     self.assertEqual(self.all_cohort_user_dict(), [model_dict])
