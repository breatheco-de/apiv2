from ..mixins.new_auth_test_case import AuthTestCase


class ReceiversTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Adding a ProfileAcademy
    """
    def test_adding_a_profile_academy(self):
        model = self.bc.database.create(profile_academy=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [])
        self.assertEqual(self.bc.format.table(model.profile_academy.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a ProfileAcademy and Group doesn't match
    """

    def test_adding_a_profile_academy__the_group_name_does_not_match(self):
        # keep separated
        model1 = self.bc.database.create(group=1)  # keep before user
        model2 = self.bc.database.create(profile_academy=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.profile_academy.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a ProfileAcademy and Group match but Role slug does't match
    """

    def test_adding_a_profile_academy__the_role_slug_does_not_match(self):
        # keep separated
        group = {'name': 'Student'}
        model1 = self.bc.database.create(group=group)  # keep before user
        model2 = self.bc.database.create(profile_academy=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.profile_academy.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a ProfileAcademy and Group match but Role slug match
    """

    def test_adding_a_profile_academy__the_group_name_and_role_slug_match(self):
        # keep separated
        group = {'name': 'Student'}
        model1 = self.bc.database.create(group=group)  # keep before user
        model2 = self.bc.database.create(profile_academy=1, role='student')

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.profile_academy.user.groups.all()), [
            self.bc.format.to_dict(model1.group),
        ])
