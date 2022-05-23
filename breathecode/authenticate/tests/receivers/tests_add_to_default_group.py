from ..mixins.new_auth_test_case import AuthTestCase


class ReceiversTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Adding a User
    """
    def test_adding_a_user(self):
        model = self.bc.database.create(user=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [])
        self.assertEqual(self.bc.format.table(model.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a User and Group doesn't match
    """

    def test_adding_a_user__the_group_name_does_not_match(self):
        # keep separated
        model1 = self.bc.database.create(group=1)  # keep before user
        model2 = self.bc.database.create(user=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a User and Group with name Default
    """

    def test_adding_a_user__the_group_name_match(self):
        group = {'name': 'Default'}
        model1 = self.bc.database.create(group=group)  # keep before user
        model2 = self.bc.database.create(user=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.user.groups.all()), [{'id': 1, 'name': 'Default'}])
