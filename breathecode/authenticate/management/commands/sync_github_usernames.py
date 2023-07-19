from breathecode.authenticate.models import GithubAcademyUser, CredentialsGithub
from django.contrib.auth.models import User

missing_usernames = GithubAcademyUser.objects.filter(username__isnull=True)
for github_user in missing_usernames:
    credential = CredentialsGithub.objects.filter(user=github_user.user).first()
    if credential is not None:
        GithubAcademyUser.objects.filter(user=credential.user).update(username=credential.username)
