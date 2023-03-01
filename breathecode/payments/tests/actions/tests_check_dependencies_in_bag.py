"""
Test /answer
"""
from unittest.mock import MagicMock, call, patch

from django.utils import timezone
from breathecode.payments.actions import check_dependencies_in_bag
from breathecode.utils.validation_exception import ValidationException

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


class PaymentsTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 With Bag
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag(self):
        model = self.bc.database.create(bag=1)
        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and Cohort without a available Plan
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__cohort_not_available_for_any_plan__because_not_exists_plans(self):
        model = self.bc.database.create(bag=1, cohort=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'cohorts-not-available-for-any-selected-plan'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__cohort_not_available_for_any_plan__because_is_not_available_in_selected_plan(self):
        plan = {'available_cohorts': []}
        model = self.bc.database.create(bag=1, cohort=1, plan=plan)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'plan-not-available-for-cohort'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and MentorshipServiceSet without a available Plan
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_not_available_for_any_plan__because_not_exists_plans(self):
        model = self.bc.database.create(bag=1, mentorship_service_set=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException,
                                      'mentorship-service-sets-not-available-for-any-selected-plan'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    patch('logging.Logger.info', MagicMock())

    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_not_available_for_any_plan__because_is_not_available_in_selected_plan(
            self):
        plan = {'available_mentorship_service_sets': []}
        model = self.bc.database.create(bag=1, mentorship_service_set=1, plan=plan)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'plan-not-available-for-mentorship-service-set'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_not_available_for_any_plan__because_not_have_mentorship_services_yet(
            self):
        model = self.bc.database.create(bag=1, mentorship_service_set=1, plan=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'mentorship-service-set-not-ready-to-be-sold'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and MentorshipServiceSet without a available Plan
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_not_available_for_any_plan__because_not_exists_plans(self):
        model = self.bc.database.create(bag=1, event_type_set=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException,
                                      'event-type-sets-not-available-for-any-selected-plan'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_not_available_for_any_plan__because_is_not_available_in_selected_plan(self):
        plan = {'available_event_type_sets': []}
        model = self.bc.database.create(bag=1, event_type_set=1, plan=plan)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'plan-not-available-for-event-type-set'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_not_available_for_any_plan__because_not_have_event_types_yet(self):
        model = self.bc.database.create(bag=1, event_type_set=1, plan=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'event-type-set-not-ready-to-be-sold'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Plan and Cohort all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__cohort_alright(self):
        model = self.bc.database.create(bag=1, cohort=1, plan=1)
        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Plan and MentorshipServiceSet all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_session_set_alright(self):
        model = self.bc.database.create(bag=1, mentorship_session_set=1, plan=1, mentorship_session=1)
        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Plan and EventTypeSet all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_alright(self):
        event_type = {'icon_url': self.bc.fake.url()}
        model = self.bc.database.create(bag=1, event_type_set=1, plan=1, event_type=event_type)
        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and Cohort without a available Service
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__cohort_not_available_for_any_plan__not_available_to_selected_service(self):
        service = {'type': 'COHORT', 'available_cohorts': []}
        model = self.bc.database.create(bag=1, cohort=1, service=service, service_item=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'service-not-available-for-cohort'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and MentorshipServiceSet without a available Service
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_not_available_for_any_plan__not_available_to_selected_service(self):
        service = {'type': 'MENTORSHIP_SERVICE_SET', 'available_mentorship_service_sets': []}
        model = self.bc.database.create(bag=1, mentorship_service_set=1, service=service, service_item=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException,
                                      'service-not-available-for-mentorship-service-set'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_not_available_for_any_plan__not_available_to_be_sold(self):
        service = {'type': 'MENTORSHIP_SERVICE_SET', 'available_mentorship_service_sets': [1]}
        model = self.bc.database.create(bag=1,
                                        mentorship_service_set=1,
                                        service=service,
                                        academy_service=1,
                                        service_item=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'mentorship-service-set-not-ready-to-be-sold'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag and EventTypeSet without a available Service
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_not_available_for_any_plan__not_available_to_selected_service(self):
        service = {'type': 'EVENT_TYPE_SET', 'available_event_type_sets': []}
        model = self.bc.database.create(bag=1, event_type_set=1, service=service, service_item=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'service-not-available-for-event-type-set'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_not_available_for_any_plan__not_available_to_be_sold(self):
        service = {'type': 'EVENT_TYPE_SET', 'available_event_type_sets': [1]}
        model = self.bc.database.create(bag=1,
                                        event_type_set=1,
                                        service=service,
                                        academy_service=1,
                                        service_item=1)
        db = self.bc.format.to_dict(model.bag)

        with self.assertRaisesMessage(ValidationException, 'event-type-set-not-ready-to-be-sold'):
            check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Service and Cohort all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__cohort_alright__in_service(self):
        service = {'type': 'COHORT', 'available_cohorts': [1]}
        model = self.bc.database.create(bag=1, cohort=1, service=service, academy_service=1, service_item=1)

        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Service and MentorshipServiceSet all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__mentorship_service_set_alright__in_service(self):
        service = {'type': 'MENTORSHIP_SERVICE_SET', 'availablementorship_service_sets': [1]}
        model = self.bc.database.create(bag=1,
                                        mentorship_service_set=1,
                                        mentorship_service=1,
                                        service=service,
                                        academy_service=1,
                                        service_item=1)

        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])

    """
    🔽🔽🔽 With Bag, Service and EventTypeSet all setup right
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_bag__event_type_set_alright__in_service(self):
        service = {'type': 'EVENT_TYPE_SET', 'available_event_type_sets': [1]}
        event_type = {'icon_url': self.bc.fake.url()}
        model = self.bc.database.create(bag=1,
                                        event_type_set=1,
                                        event_type=event_type,
                                        service=service,
                                        academy_service=1,
                                        service_item=1)

        db = self.bc.format.to_dict(model.bag)

        check_dependencies_in_bag(model.bag, 'en')

        self.assertEqual(self.bc.database.list_of('payments.Bag'), [db])
