from unittest.mock import patch, call, MagicMock
from breathecode.tests.mocks.django_contrib import DJANGO_CONTRIB_PATH, apply_django_contrib_messages_mock
from breathecode.jobs.services import ScraperFactory
from ..mixins import JobsTestCase


class ServicesGetClassScraperFactoryTestCase(JobsTestCase):
    @patch(DJANGO_CONTRIB_PATH['messages'], apply_django_contrib_messages_mock())
    @patch('django.contrib.messages.add_message', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_return_false(self):

        from logging import Logger
        try:
            ScraperFactory('torta')
            assert False
        except Exception as e:
            print(str(e))
