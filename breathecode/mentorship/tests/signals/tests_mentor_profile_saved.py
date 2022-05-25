from ..mixins import MentorshipTestCase


class ReceiversTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Adding a ProfileAcademy
    """
    def test_adding_a_mentor_profile(self):
        model = self.bc.database.create(mentor_profile=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [])
        self.assertEqual(self.bc.format.table(model.mentor_profile.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a ProfileAcademy and Group doesn't match
    """

    def test_adding_a_mentor_profile__the_group_name_does_not_match(self):
        # keep separated
        model1 = self.bc.database.create(group=1)  # keep before user
        model2 = self.bc.database.create(mentor_profile=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.mentor_profile.user.groups.all()), [])

    """
    🔽🔽🔽 Adding a ProfileAcademy and Group match
    """

    def test_adding_a_mentor_profile__the_group_name_match(self):
        # keep separated
        group = {'name': 'Mentor'}
        model1 = self.bc.database.create(group=group)  # keep before user
        model2 = self.bc.database.create(mentor_profile=1)

        self.assertEqual(self.bc.database.list_of('auth.Group'), [self.bc.format.to_dict(model1.group)])
        self.assertEqual(self.bc.format.table(model2.mentor_profile.user.groups.all()), [
            self.bc.format.to_dict(model1.group),
        ])
