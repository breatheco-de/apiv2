from datetime import timedelta
import random
import sys
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase
import breathecode.events.tasks as tasks
from breathecode.events.management.commands.fix_live_class_dates import Command
from django.utils import timezone
from breathecode.events import tasks

UTC_NOW = timezone.now()
DELTA = timedelta(seconds=60 * random.randint(0, 61), minutes=random.randint(31, 61))


class TestSyncOrgVenues(LegacyAPITestCase):
    # When: no LiveClass and no Cohort exists
    # Then: nothing should happen
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.tasks.fix_live_class_dates.delay', MagicMock())
    @patch('breathecode.admissions.signals.timeslot_saved.send', MagicMock())
    @patch.object(sys.stdout, 'write', MagicMock())
    @patch.object(sys.stderr, 'write', MagicMock())
    def test_0_live_classes(self):

        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

        self.bc.check.calls(tasks.fix_live_class_dates.delay.call_args_list, [])
        self.bc.check.calls(sys.stdout.write.call_args_list, [
            call('Found 0 cohorts that have not finished and should have live classes\n'),
        ])
        self.bc.check.calls(sys.stderr.write.call_args_list, [])

    # When: a Cohort exists and it's starting_at is less than now
    # Then: nothing should happen
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.tasks.fix_live_class_dates.delay', MagicMock())
    @patch('breathecode.admissions.signals.timeslot_saved.send', MagicMock())
    @patch.object(sys.stdout, 'write', MagicMock())
    @patch.object(sys.stderr, 'write', MagicMock())
    def test_2_cohorts__in_the_past(self):

        cohorts = [{'never_ends': False, 'ending_date': UTC_NOW - DELTA} for _ in range(2)]
        model = self.bc.database.create(cohort=cohorts)
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(
            self.bc.database.list_of('admissions.Cohort'),
            self.bc.format.to_dict(model.cohort),
        )

        self.bc.check.calls(tasks.fix_live_class_dates.delay.call_args_list, [])
        self.bc.check.calls(sys.stdout.write.call_args_list, [
            call('Found 0 cohorts that have not finished and should have live classes\n'),
        ])
        self.bc.check.calls(sys.stderr.write.call_args_list, [])

    # When: a Cohort exists and it's starting_at is less than now
    # Then: found 2 cohorts without timeslots
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.tasks.fix_live_class_dates.delay', MagicMock())
    @patch('breathecode.admissions.signals.timeslot_saved.send', MagicMock())
    @patch.object(sys.stdout, 'write', MagicMock())
    @patch.object(sys.stderr, 'write', MagicMock())
    def test_2_cohorts__in_the_future(self):

        cohorts = [{'never_ends': False, 'ending_date': UTC_NOW + DELTA} for _ in range(2)]
        model = self.bc.database.create(cohort=cohorts)
        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(
            self.bc.database.list_of('admissions.Cohort'),
            self.bc.format.to_dict(model.cohort),
        )

        self.bc.check.calls(tasks.fix_live_class_dates.delay.call_args_list, [])
        self.bc.check.calls(sys.stdout.write.call_args_list, [
            call('Found 2 cohorts that have not finished and should have live classes\n'),
        ])
        self.bc.check.calls(sys.stderr.write.call_args_list, [])

    # When: 2 LiveClass and 2 Cohort exists and it's starting_at is greater than now
    # Then: nothing should happen
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.tasks.fix_live_class_dates.delay', MagicMock())
    @patch('breathecode.admissions.signals.timeslot_saved.send', MagicMock())
    @patch.object(sys.stdout, 'write', MagicMock())
    @patch.object(sys.stderr, 'write', MagicMock())
    def test_2_live_classes(self):

        live_classes = [{
            'cohort_time_slot_id': n,
            'starting_at': UTC_NOW + DELTA,
        } for n in range(1, 5)]
        cohorts = [{'never_ends': False, 'ending_date': UTC_NOW + DELTA} for _ in range(2)]
        cohort_time_slots = [{'cohort_id': 1} for n in range(2)]
        cohort_time_slots += [{'cohort_id': 2} for n in range(2)]
        model = self.bc.database.create(live_class=live_classes, cohort=cohorts, cohort_time_slot=cohort_time_slots)

        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), self.bc.format.to_dict(model.live_class))

        self.bc.check.calls(tasks.fix_live_class_dates.delay.call_args_list, [
            call(1),
            call(2),
            call(3),
            call(4),
        ])
        self.bc.check.calls(sys.stdout.write.call_args_list, [
            call('Found 2 cohorts that have not finished and should have live classes\n'),
            call(f'Adding cohort {model.cohort[0].slug} to the fixing queue, it ends on '
                 f'{model.cohort[0].ending_date}\n'),
            call(f'Adding cohort {model.cohort[1].slug} to the fixing queue, it ends on '
                 f'{model.cohort[1].ending_date}\n'),
        ])
        self.bc.check.calls(sys.stderr.write.call_args_list, [])
