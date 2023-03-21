from breathecode.authenticate.models import User
from breathecode.services import LaunchDarkly


def user(client: LaunchDarkly, user: User):
    key = f'user-{user.id}'
    name = f'{user.first_name} {user.last_name} ({user.email})'
    kind = 'user-data'
    context = {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'groups': [x.name for x in user.groups.all()],
    }

    return client.context(key, name, kind, context)
