"""
Collections of mixins used to login in authorize microservice
"""


class MarketingQueriesMixin:

    def generate_marketing_queries(self):
        """Generate queries"""
        return {
            "module": "marketing",
            "models": [
                "ActiveCampaignAcademy",
                "Automation",
                "Tag",
                "Contact",
                "LeadGenerationApp",
                "FormEntry",
                "ShortLink",
                "AcademyAlias",
                "ActiveCampaignWebhook",
                "Downloadable",
            ],
        }
