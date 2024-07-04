from breathecode.authenticate.models import User
from breathecode.services import LaunchDarkly


def user(client: LaunchDarkly, user: User):
    key = f"{user.id}"
    name = f"{user.first_name} {user.last_name} ({user.email})"
    kind = "user"
    context = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "date_joined": user.date_joined,
        "groups": [x.name for x in user.groups.all()],
    }

    return client.context(key, name, kind, context)
