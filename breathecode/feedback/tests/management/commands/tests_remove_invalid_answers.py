import random
from unittest.mock import MagicMock, call, patch
from ...mixins import FeedbackTestCase
from breathecode.feedback.management.commands.remove_invalid_answers import Command
import sys


class TokenTestSuite(FeedbackTestCase):

    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock())
    @patch('breathecode.feedback.signals.survey_answered.send', MagicMock())
    @patch('sys.stdout.write', MagicMock())
    @patch('sys.stderr.write', MagicMock())
    def test_run_handler(self):
        surveys = [{'cohort_id': n} for n in range(1, 4)]
        cohort_users = [{'cohort_id': n, 'user_id': n} for n in range(1, 4)]
        answers = [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['ANSWERED', 'OPENED']),
            'score': random.randint(1, 10),
        } for n in range(1, 4)] + [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['PENDING', 'SENT', 'EXPIRED']),
            'score': None,
        } for n in range(1, 4)] + [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['ANSWERED', 'OPENED']),
            'score': None,
        } for n in range(1, 4)] + [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['ANSWERED', 'OPENED']),
            'score': random.randint(1, 10),
        } for n in range(1, 4)] + [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['PENDING', 'SENT', 'EXPIRED']),
            'score': None,
        } for n in range(1, 4)] + [{
            'survey_id': n,
            'cohort_id': n,
            'user_id': n,
            'status': random.choice(['ANSWERED', 'OPENED']),
            'score': None,
        } for n in range(1, 4)]

        model = self.bc.database.create(user=3,
                                        survey=surveys,
                                        answer=answers,
                                        cohort=3,
                                        cohort_user=cohort_users)

        answer_db = self.bc.format.to_dict(model.answer)

        command = Command()
        command.handle()

        self.assertEqual(self.bc.database.list_of('feedback.Survey'), self.bc.format.to_dict(model.survey))

        # this ignore the answers is not answered or opened
        self.assertEqual(self.bc.database.list_of('feedback.Answer'), [
            self.bc.format.to_dict(answer_db[0]),
            self.bc.format.to_dict(answer_db[1]),
            self.bc.format.to_dict(answer_db[2]),
            self.bc.format.to_dict(answer_db[6]),
            self.bc.format.to_dict(answer_db[7]),
            self.bc.format.to_dict(answer_db[8]),
            self.bc.format.to_dict(answer_db[9]),
            self.bc.format.to_dict(answer_db[10]),
            self.bc.format.to_dict(answer_db[11]),
            self.bc.format.to_dict(answer_db[15]),
            self.bc.format.to_dict(answer_db[16]),
            self.bc.format.to_dict(answer_db[17]),
        ])

        self.assertEqual(sys.stdout.write.call_args_list, [call('Successfully deleted invalid answers\n')])
        self.assertEqual(sys.stderr.write.call_args_list, [])
