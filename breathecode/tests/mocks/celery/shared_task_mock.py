def delay():
    pass


# def shared_task(func, **kwargs):
#     def wrapper(*args, **kwargs):
#         func(None, *args, **kwargs)

#     wrapper.delay = delay
#     return wrapper


def decorator(func, with_self=True):

    def wrapper(*args, **kwargs):
        if with_self:
            func(None, *args, **kwargs)
        else:
            func(*args, **kwargs)

    wrapper.delay = delay
    return wrapper


def shared_task(func=None, *args, **kwargs):

    def inner(func):
        return decorator(func)

    if func:
        return decorator(func, with_self=False)

    return inner  # this is the fun_obj mentioned in the above content
