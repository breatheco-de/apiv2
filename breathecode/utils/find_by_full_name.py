from django.db.models import Q

__all__ = ["query_like_by_full_name"]


def query_like_by_full_name(prefix="", **kwargs):
    first_name_kwargs = prefix + "first_name__icontains"
    last_name_kwargs = prefix + "last_name__icontains"
    email_kwargs = prefix + "email__icontains"
    items = kwargs["items"]
    for query in kwargs["like"].split():
        items = kwargs["items"].filter(
            Q(**{first_name_kwargs: query}) | Q(**{last_name_kwargs: query}) | Q(**{email_kwargs: query})
        )
    return items
