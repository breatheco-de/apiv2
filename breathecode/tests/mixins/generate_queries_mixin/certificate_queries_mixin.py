"""
Collections of mixins used to login in authorize microservice
"""


class CertificateQueriesMixin:

    def generate_certificate_queries(self):
        """Generate queries"""
        return {"module": "certificate", "models": ["Specialty", "Badge", "LayoutDesign", "UserSpecialty"]}
