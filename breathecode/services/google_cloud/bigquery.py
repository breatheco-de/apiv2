import logging

import google.cloud.bigquery as bigquery

from .credentials import resolve_credentials

logger = logging.getLogger(__name__)

__all__ = ['BigQuery']


class BigQuery:
    """Google BigQuery"""

    def __init__(self):
        resolve_credentials()

    def query_dataset(self, table_name, table_args, query, ds, columns):
        client = bigquery.Client()
        dataset_ref = client.dataset(ds)
        table = dataset_ref.table(table_name)

        query_filter = ' AND '.join(f"{key} = '{value}'" for key, value in query.items())
        query_string = f"SELECT {', '.join(columns)} FROM {table.full_table_id} WHERE {query_filter}"

        query_job = client.query(query_string)
        results = query_job.result()

        rows = []
        for row in results:
            row_dict = {}
            for column in columns:
                row_dict[column] = row[column]
            rows.append(row_dict)

        return rows
