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
    print('asddddddddddddddddddddd111')

    if func:
        return decorator(func, with_self=False)

    print('asddddddddddddddddddddd222')

    return inner #this is the fun_obj mentioned in the above content 
  

# @shared_task(aaaaa=1, bbbb=2)
# def main(self, a):
#     print('rrrrrrrrrrrrrrrrr', a)

# print(main)
# print(main(11111))

# @shared_task()
# def main(self, a):
#     print('rrrrrrrrrrrrrrrrr', a)

# print(main)
# print(main(22222))

# @shared_task
# def main(a):
#     print('rrrrrrrrrrrrrrrrr', a)

# print(main)
# print(main(33333))
