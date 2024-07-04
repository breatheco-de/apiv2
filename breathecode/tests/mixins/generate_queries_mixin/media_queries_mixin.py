"""
Collections of mixins used to login in authorize microservice
"""


class MediaQueriesMixin:

    def generate_media_queries(self):
        """Generate queries"""
        return {"module": "media", "models": ["Category", "Media", "MediaResolution"]}
