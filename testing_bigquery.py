from google.cloud import bigquery
import os
import django
import datetime

# Set the DJANGO_SETTINGS_MODULE environment variable to your project's settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathecode.settings')

# Manually initialize Django
django.setup()

from breathecode.services.google_cloud.big_query import BigQuery

client = None


class Sum():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class Count():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class Avg():

    def __init__(self, param):
        self._constructor_args = ((param, ), )


class BigQuerySet():

    def __init__(self, table):
        self.query = {}
        self.agg = []
        self.fields = None
        self.group = None
        self.table = table

    def set_query(self, *args, **kwargs):
        self.query.update(kwargs)

    def order_by(self, *name):
        self.group = name
        return self

    def aggregate(self, *args):
        sql = self.sql(args)
        print(sql)
        params, kwparams = self.get_params()

        client, project_id, dataset = BigQuery.client()
        # print('params')
        # print(params)
        # print('kwparams')
        # print(kwparams)
        print('EPALEEE')
        print(sql[0:1])
        print(sql[1:44])
        query_job = client.query(sql, *params, **kwparams)
        # print(dir(query_job))
        return query_job.result()

    def build(self):
        sql = self.sql()
        params, kwparams = self.get_params()

        query_job = client.query(sql, *params, **kwparams)
        return query_job.results()

    def filter(self, *args, **kwargs):
        self.set_query(*args, **kwargs)
        return self

    def attribute_parser(self, key):
        operand = '='
        key = key.replace('__', '.')
        if key[-4:] == '.gte':
            key = key[:-4]
            operand = '>='
        elif key[-3:] == '.gt':
            key = key[:-3]
            operand = '>'
        elif key[-3:] == '.lt':
            key = key[:-3]
            operand = '<'
        if key[-4:] == '.lte':
            key = key[:-4]
            operand = '<='
        return key, operand, '__' + key.replace('.', '__')

    def get_type(self, elem):
        if isinstance(elem, int):
            return 'INT64'
        if isinstance(elem, float):
            return 'FLOAT64'
        if isinstance(elem, bool):
            return 'BOOL'
        if isinstance(elem, str):
            return 'STRING'
        if isinstance(elem, datetime):
            return 'DATETIME'

    def get_params(self):
        if not self.query:
            return [], {}
        params = []
        kwparams = {}
        query_params = []

        for key, val in self.query.items():
            key, operand, var_name = self.attribute_parser(key)
            query_params.append(bigquery.ScalarQueryParameter(var_name, self.get_type(val), val))

        job_config = bigquery.QueryJobConfig(destination=f'breathecode-197918.4geeks_dev.konoha',
                                             query_parameters=query_params)
        kwparams['job_config'] = job_config

        return params, kwparams

    def select(self, *names):
        self.fields = names
        return self

    def aggregation_parser(self, agg):
        operation = None
        attribute = None
        if isinstance(agg, Sum):
            operation = 'SUM'
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Count):
            operation = 'COUNT'
            attribute = agg._constructor_args[0][0]

        if isinstance(agg, Avg):
            operation = 'AVG'
            attribute = agg._constructor_args[0][0]

        return operation, attribute

    def sql(self, aggs=[]):
        query_fields = []
        if self.fields:
            query_fields += self.fields
        if aggs:
            for agg in aggs:
                operation, attribute = self.aggregation_parser(agg)
                query_fields.append(f'{operation}({attribute}) AS {attribute}')

        # if aggs:
        #     query = f'SELECT '
        #     for agg in aggs:
        #         operation, attribute = self.aggregation_parser(agg)
        #         query += f'{operation}({attribute}) AS {attribute}, '
        #     query = query[:-2]
        #     query += f' FROM {self.table} '
        # elif self.fields:
        #     query = f'SELECT {", ".join(self.fields)} FROM {self.table}'

        # else:
        #     query = f'SELECT * FROM {self.table} '

        if len(query_fields) > 0:
            query = f"""SELECT {", ".join(query_fields)} FROM `4geeks-dev.{self.table}` """
        else:
            query = f"""SELECT * FROM `4geeks-dev.{self.table}` """

        if self.query:
            query += 'WHERE '
            for key, val in self.query.items():
                key, operand, var_name = self.attribute_parser(key)
                query += f'{key} {operand} @{var_name} AND '
            query = query[:-5]

        if self.group:
            group_by = ', '.join(self.group)
            query += f' GROUP BY {group_by}'

        return query


attribute = BigQuerySet('konoha')

result = attribute.filter(id=1, age=4, date__gte=8, subtable__chakra__gt=7, start__lte=6, chakra__lt=19)
result = attribute.select('name', 'hokage')
result = attribute.order_by('name', 'location')
print(result.sql())
print(result.get_params())
print(result.aggregate(Sum('age')))
