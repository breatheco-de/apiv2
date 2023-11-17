from google.cloud import bigquery


class Sum():

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

    def aggregate(self, *args):
        sql = self.sql(args)
        print(sql)
        params, kwparams = self.get_params()

        query_job = client.query(sql, *params, **kwparams)
        return query_job.results()

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
        return key, operand, '__' + key.replace('.', '__')

    def get_type(self, elem):
        if isinstance(elem, int):
            return 'INT64'

    def get_params(self):
        if not self.query:
            return [], {}
        params = []
        kwparams = {}
        query_params = []

        for key, val in self.query.items():
            key, operand, var_name = self.attribute_parser(key)
            query_params.append(bigquery.ScalarQueryParameter(var_name, self.get_type(val), val))

        job_config = bigquery.QueryJobConfig(destination=f'breathecode.4geeks-dev.konoha',
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

        return operation, attribute

    def sql(self, aggs=[]):
        if aggs:
            query = f'SELECT '
            for agg in aggs:
                operation, attribute = self.aggregation_parser(agg)
                query += f'{operation}({attribute}) AS {attribute}, '
            query = query[:-2]
            query += f' FROM {self.table} '
        elif self.fields:
            query = f'SELECT {", ".join(self.fields)} FROM {self.table}'

        else:
            query = f'SELECT * FROM {self.table} '

        if self.query:
            query += 'WHERE '
            for key, val in self.query.items():
                key, operand, var_name = self.attribute_parser(key)
                query += f'{key} {operand} @{var_name} AND '
            query = query[:-5]
        return query


attribute = BigQuerySet('konoha')

result = attribute.filter(id=1, age=4, name__gte=8, subtable__chakra__gt=7)
print(result.sql())
print(result.get_params())
print(result.aggregate(Sum('age')))
