def paginated_datastore(public_iter):
    count = len(public_iter)

    return {'count': count, 'result': public_iter}
