from django.db.models import Q

def query_like_by_full_name(like, items, prefix):
    a_kwargs = {'first_name': f'{prefix}first_name__icontains'}
    b_kwargs = {f'{prefix}last_name__icontains': f'{prefix}last_name__icontains'}
    c_kwargs = {f'{prefix}email__icontains': f'{prefix}email__icontains'}
    for query in like.split():
        items = items.filter(Q(a_kwargs=query) | Q(
                b_kwargs=query) | Q(c_kwargs=query))
    return items