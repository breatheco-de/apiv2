from django.db.models import Q

def query_like_by_full_name(like, items):
    for query in like.split():
        items = items.filter(Q(first_name__icontains=query) | Q(
                last_name__icontains=query) | Q(email__icontains=query))
    return items