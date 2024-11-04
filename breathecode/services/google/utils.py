from breathecode.authenticate.models import CredentialsGoogle

from ..google_meet import GoogleMeet


def get_client(credentials: CredentialsGoogle) -> GoogleMeet:
    return GoogleMeet(credentials.token, credentials.refresh_token)
