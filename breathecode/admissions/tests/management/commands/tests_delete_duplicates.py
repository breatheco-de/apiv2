"""
Test /academy/cohort
"""
from mixer.backend.django import mixer

from ...mixins import AdmissionsTestCase
from ....management.commands.delete_duplicates import Command


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""
    def test_delete_duplicates(self):
        """Test /academy/cohort without auth"""
        model = self.generate_models(cohort=True, user=True)
        models = [
            mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort'])
            for _ in range(0, 10)
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
    #     model = self.generate_models(cohort=True, user=True)

    #     rand_start = randint(0, 9)
    #     rand_end = randint(0, 9)

    #     models = (
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort']) for _ in
    #             range(0, rand_start)] +
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort'],
    #             educational_status='GRADUATED')] +
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort']) for _ in
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
    #     model = self.generate_models(cohort=True, user=True)

    #     rand_start = randint(0, 9)
    #     rand_end = randint(0, 9)

    #     models = (
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort']) for _ in
    #             range(0, rand_start)] +
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort'],
    #             finantial_status='LATE')] +
    #         [mixer.blend('admissions.CohortUser', user=model['user'], cohort=model['cohort']) for _ in
    #             range(0, rand_end)]
    #     )
    #     model_dict = self.remove_dinamics_fields(models[rand_start].__dict__)
    #     command = Command()

    #     self.assertEqual(command.cohort_users(), None)
    #     self.assertEqual(self.count_cohort_user(), 1)
    #     self.assertEqual(self.all_cohort_user_dict(), [model_dict])
