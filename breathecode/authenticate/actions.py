from django.contrib.auth.models import User, Group

def get_user(github_id=None, email=None):
    user = None
    if email is not None:
        user = User.objects.get(email=email)
    return user

def create_user(github_id=None, email=None):
    user = None
    if email is not None:
        user = User.objects.get(email=email)
    return user