import logging

from google.cloud import bigquery

from .credentials import resolve_credentials

logger = logging.getLogger(__name__)

__all__ = ['Bigquery']


class Bigquery:
    """Google Bigquery"""

    def __init__(self):
        resolve_credentials()

    def query_bigquery_dataset(query, ds, columns):
        client = bigquery.Client()
        dataset_ref = client.dataset(ds)
        table = dataset_ref.table('your_table_name')  # Replace with your table name

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
