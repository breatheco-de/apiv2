"""
Run once decorator
"""


def run_once(function):
    """Run function just once"""
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return function(*args, **kwargs)

    wrapper.has_run = False
    return wrapper
