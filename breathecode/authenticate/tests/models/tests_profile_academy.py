"""
Regression tests for ProfileAcademy deferred-field / __init__ safety.
"""

from breathecode.authenticate.models import ProfileAcademy

from ..mixins.new_auth_test_case import AuthTestCase


class ProfileAcademyModelTestSuite(AuthTestCase):
    """
    .only("phone") used to RecursionError because ProfileAcademy.__init__
    accessed the role FK via its descriptor.
    """

    def test_only_phone_does_not_raise_recursion_error(self):
        model = self.generate_models(
            profile_academy={"phone": "+15552222222"},
            role="student",
        )

        instance = ProfileAcademy.objects.filter(id=model.profile_academy.id).only("phone").first()

        self.assertIsNotNone(instance)
        self.assertEqual(instance.phone, "+15552222222")
        self.assertIsNone(instance._ProfileAcademy__old_role_id)
