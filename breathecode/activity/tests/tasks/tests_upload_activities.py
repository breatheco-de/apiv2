"""
Test /answer
"""
from datetime import date, datetime
import logging
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from django.utils import timezone
from breathecode.services.google_cloud.big_query import BigQuery

from breathecode.activity.tasks import add_activity
from breathecode.activity import actions
from google.cloud import bigquery

from ..mixins import MediaTestCase

UTC_NOW = timezone.now()


def bigquery_client_mock(user_id=1,
                         kind=None,
                         meta={},
                         related_type=None,
                         related_id=None,
                         related_slug=None,
                         fail=None):

    result_mock = MagicMock()

    if fail:
        result_mock.done.return_value = True
        result_mock.error_result = {'message': fail}

    else:
        result_mock.done.return_value = False
        result_mock.error_result = None

    client_mock = MagicMock()
    client_mock.query.return_value = result_mock

    project_id = 'test'
    dataset = '4geeks'

    meta_struct = ''

    job_config = bigquery.QueryJobConfig(
        destination=f'{project_id}.{dataset}.activity',
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        query_parameters=[
            bigquery.ScalarQueryParameter('x__id', 'STRING',
                                          uuid4().hex),
            bigquery.ScalarQueryParameter('x__user_id', 'INT64', user_id),
            bigquery.ScalarQueryParameter('x__kind', 'STRING', kind),
            bigquery.ScalarQueryParameter('x__timestamp', 'TIMESTAMP',
                                          timezone.now().isoformat()),
            bigquery.ScalarQueryParameter('x__related_type', 'STRING', related_type),
            bigquery.ScalarQueryParameter('x__related_id', 'INT64', related_id),
            bigquery.ScalarQueryParameter('x__related_slug', 'STRING', related_slug),
        ])

    for key in meta:
        t = 'STRING'
        if isinstance(meta[key], str):
            pass
        elif isinstance(meta[key], int):
            t = 'INT64'
        elif isinstance(meta[key], float):
            t = 'FLOAT64'
        elif isinstance(meta[key], bool):
            t = 'BOOL'
        elif isinstance(meta[key], datetime):
            t = 'TIMESTAMP'
        elif isinstance(meta[key], date):
            t = 'DATE'

        job_config.query_parameters.append(bigquery.ScalarQueryParameter(key, t, meta[key]))
        meta_struct += f'@{key} as {key}, '

    if meta_struct:
        meta_struct = meta_struct[:-2]

    query = f"""
        SELECT
            @x__id as id,
            @x__user_id as user_id,
            @x__kind as kind,
            @x__timestamp as timestamp,
            STRUCT(
                @x__related_type as type,
                @x__related_id as id,
                @x__related_slug as slug) as related,
            STRUCT({meta_struct}) as meta
    """

    return (client_mock, result_mock, query, project_id, dataset)


# upload_activities


class MediaTestSuite(MediaTestCase):

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    @patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value={}))
    def test_type_and_no_id_or_slug(self):
        kind = self.bc.fake.slug()

        val = bigquery_client_mock(user_id=1, kind=kind)
        (client_mock, result_mock, _, project_id, dataset) = val

        with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
            mock.return_value = (client_mock, project_id, dataset)
            add_activity.delay(1, kind, related_type='auth.User')

            self.bc.check.calls(BigQuery.client.call_args_list, [])
            self.bc.check.calls(result_mock.done.call_args_list, [])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call(
                'If related_type is provided, either related_id or related_slug must be provided, '
                'but not both.',
                exc_info=True),
        ])
        self.bc.check.calls(actions.get_activity_meta.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    @patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value={}))
    def test_type_with_id_and_slug(self):
        kind = self.bc.fake.slug()

        val = bigquery_client_mock(user_id=1, kind=kind)
        (client_mock, result_mock, _, project_id, dataset) = val

        with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
            mock.return_value = (client_mock, project_id, dataset)
            add_activity.delay(1, kind, related_id=1, related_slug='slug')

            self.bc.check.calls(BigQuery.client.call_args_list, [])
            self.bc.check.calls(result_mock.done.call_args_list, [])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [
            call('If related_type is not provided, both related_id and related_slug must also be absent.',
                 exc_info=True),
        ])
        self.bc.check.calls(actions.get_activity_meta.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    @patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value={}))
    def test_adding_the_resource_with_id_and_no_meta(self):
        kind = self.bc.fake.slug()

        val = bigquery_client_mock(user_id=1, kind=kind, meta={})
        (client_mock, result_mock, query, project_id, dataset) = val

        logging.Logger.info.call_args_list = []

        with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
            mock.return_value = (client_mock, project_id, dataset)
            add_activity.delay(1, kind, related_type='auth.User', related_id=1)

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == query
            self.bc.check.calls(result_mock.done.call_args_list, [call()])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(actions.get_activity_meta.call_args_list, [call(kind, 'auth.User', 1, None)])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    @patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value={}))
    def test_adding_the_resource_with_slug_and_no_meta(self):
        kind = self.bc.fake.slug()

        val = bigquery_client_mock(user_id=1, kind=kind, meta={})
        (client_mock, result_mock, query, project_id, dataset) = val

        logging.Logger.info.call_args_list = []

        related_slug = self.bc.fake.slug()

        with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
            mock.return_value = (client_mock, project_id, dataset)
            add_activity.delay(1, kind, related_type='auth.User', related_slug=related_slug)

            self.bc.check.calls(BigQuery.client.call_args_list, [call()])
            assert client_mock.query.call_args[0][0] == query
            self.bc.check.calls(result_mock.done.call_args_list, [call()])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

        self.bc.check.calls(actions.get_activity_meta.call_args_list,
                            [call(kind, 'auth.User', None, related_slug)])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    def test_adding_the_resource_with_meta(self):
        kind = self.bc.fake.slug()

        meta = {
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
        }

        val = bigquery_client_mock(user_id=1, kind=kind, meta=meta, related_type='auth.User', related_id=1)
        (client_mock, result_mock, query, project_id, dataset) = val

        logging.Logger.info.call_args_list = []

        with patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value=meta)):
            with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
                mock.return_value = (client_mock, project_id, dataset)
                add_activity.delay(1, kind, related_type='auth.User', related_id=1)

                self.bc.check.calls(BigQuery.client.call_args_list, [call()])
                assert client_mock.query.call_args[0][0] == query
                self.bc.check.calls(result_mock.done.call_args_list, [call()])
                self.bc.check.calls(actions.get_activity_meta.call_args_list, [
                    call(kind, 'auth.User', 1, None),
                ])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.services.google_cloud.credentials.resolve_credentials', MagicMock())
    def test_adding_the_resource_with_meta__it_fails(self):
        kind = self.bc.fake.slug()

        meta = {
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
            self.bc.fake.slug().replace('-', '_'): self.bc.fake.slug(),
        }

        exc = self.bc.fake.slug()

        val = bigquery_client_mock(user_id=1,
                                   kind=kind,
                                   meta=meta,
                                   related_type='auth.User',
                                   related_id=1,
                                   fail=exc)
        (client_mock, result_mock, query, project_id, dataset) = val

        logging.Logger.info.call_args_list = []

        with patch('breathecode.activity.actions.get_activity_meta', MagicMock(return_value=meta)):
            with patch('breathecode.services.google_cloud.big_query.BigQuery.client') as mock:
                mock.return_value = (client_mock, project_id, dataset)
                add_activity.delay(1, kind, related_type='auth.User', related_id=1)

                self.bc.check.calls(BigQuery.client.call_args_list, [call()])
                assert client_mock.query.call_args[0][0] == query
                self.bc.check.calls(result_mock.done.call_args_list, [call()])
                self.bc.check.calls(actions.get_activity_meta.call_args_list, [
                    call(kind, 'auth.User', 1, None),
                ])

        self.bc.check.calls(logging.Logger.info.call_args_list,
                            [call(f'Executing add_activity related to {kind}')])
        self.bc.check.calls(logging.Logger.error.call_args_list, [call(exc, exc_info=True)])
