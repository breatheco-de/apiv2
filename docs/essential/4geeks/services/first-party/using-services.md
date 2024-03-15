# Using services

We have a wrapper that manages the authentication to any [first-party](../introduction.md) service.

## Arguments

Both, the [class](<https://en.wikipedia.org/wiki/Class_(computer_programming)>) `Service` and the function `service` accepts the following arguments:

- `app_pk`: `app.id` or `app.slug`.
- `user_pk`: `user.id`.
- `mode`: `"signature"` or `"jwt"`.

## Signature mode vs JWT mode

When JWT is used, it just signs a token with the data of the user, while the signature signs the token with all the content of the request to verify the source of the request. JWT is significantly faster than using signatures.

## Syncronomous implementation

Service is a [Requests](../../../requests.md) wrapper, you should use this library like it was Requests, and the [host](https://en.wikipedia.org/wiki/Hostname) is resolved automatically.

### making a request signed in as 4geeks

```py
from breathecode.utils.service import Service

try:
    s = Service('rigobot')
    response = s.get('/my/path')
    data = response.json()

except Exception:
    # not found exception
```

### making a request signed in as a 4geeks user.

```py
from breathecode.utils.service import Service

try:
    s = Service('rigobot', 1)
    response = s.get('/my/path')
    data = response.json()

except Exception:
    # not found exception
```

## Asyncronomous implementation

Service is a [AIOHTTP](../../../aiohttp.md) wrapper, you should use this library like it was AIOHTTP, and the [host](https://en.wikipedia.org/wiki/Hostname) is resolved automatically.

### making a request signed in as 4geeks

```py
from django.core.exceptions import SynchronousOnlyOperation
from breathecode.utils.service import service

try:
    s = await service('rigobot')

except SynchronousOnlyOperation:
    # exception about that the worker does not support asynchronous code

except Exception:
    # not found exception

# If all went well
async with s:
    async with s.get('/my/path') as response:
        data = await response.json()
```

### making a request signed in as a 4geeks user.

```py
from django.core.exceptions import SynchronousOnlyOperation
from breathecode.utils.service import service

try:
    s = await service('rigobot', 1)

except SynchronousOnlyOperation:
    # exception about that the worker does not support asynchronous code

except Exception:
    # not found exception

# If all went well
async with s:
    async with s.get('/my/path') as response:
        data = await response.json()
```

### Why does it use aget instead of get

Because initially this was made to contain both styles, synchronous and asynchronous, aget means asynchronous get, this difference should be removed by implementing the context API over the `Service` class.

## Why the implementation differ

[AIOHTTP](../../../aiohttp.md) requires the use of the context API and [Requests](../../../requests.md) does not, and [Python](https://www.python.org/) does not support [asyncronomous](<https://en.wikipedia.org/wiki/Asynchrony_(computer_programming)>) [constructors](<https://en.wikipedia.org/wiki/Constructor_(object-oriented_programming)>), I could not implement a constructor that was compatible with syncronomous and asyncronomous code, I am thinking about update this implementation in the future to reduce the difference between them using the context API.
