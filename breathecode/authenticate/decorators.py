from rest_framework.exceptions import PermissionDenied

def allowed_users(allowed_roles=[]):
    def wrapper_func(request, *args, **kwargs):
        print("Allowed roles", allowed_roles)

        groups = requets.user.groups.all()
        if len(groups) == 0:
            raise PermissionDenied("You don't belong to any groups")
        elif len(list(set(a) & set(b))) == 0:
            raise PermissionDenied("You don't have permissions for request")

        return view_func(request, *args, **kwargs)
    return wrapper_func