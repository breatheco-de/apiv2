"""
Collections of mixins used to login in authorize microservice
"""


class MonitoringQueriesMixin:

    def generate_monitoring_queries(self):
        """Generate queries"""
        return {"module": "monitoring", "models": ["Application", "Endpoint", "MonitorScript"]}
