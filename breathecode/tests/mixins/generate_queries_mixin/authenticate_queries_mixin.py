"""
Collections of mixins used to login in authorize microservice
"""


class AuthenticateQueriesMixin:

    def generate_authenticate_queries(self):
        """Generate queries"""
        return {
            "module": "authenticate",
            "models": [
                "Profile",
                "Capability",
                "Role",
                "UserInvite",
                "ProfileAcademy",
                "CredentialsGithub",
                "CredentialsSlack",
                "CredentialsFacebook",
                "CredentialsQuickBooks",
                "Token",
                "DeviceId",
            ],
        }
