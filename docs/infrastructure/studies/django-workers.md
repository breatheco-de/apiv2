# Better Django worker

This article is based fundamentally on which option is better in efficiency and features, we are covering three libraries because they were popular choices by the community.

## Collected workers

### Gevent

[Gevent](http://www.gevent.org/) patches many system libraries to become cooperative and it does that the worker works as if this were asynchronous but over WSGI, but this does not allow running asynchronous code.

### Uvicorn

[Uvicorn](https://www.uvicorn.org/) is an ASGI implementation for Python, it is known as a faster worker until now.

### Hypercorn

[Hypercorn](https://pgjones.gitlab.io/hypercorn/) is an ASGI implementation for Python, it is a good option compared with Uvicorn.

## Source of Truth

I needed to see how should impact the blocking code to the web worker, I wrote `Gevent vs Uvicorn vs Hypercorn` to cover this purpose, this is the next charset of `Requests vs HTTPX vs AIOHTTP`.

### Source

- [Requests vs HTTPX vs AIOHTTP](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/http)
- [Gevent vs Uvicorn vs Hypercorn](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/django-workers/)

### Result

- [Requests vs HTTPX vs AIOHTTP](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/http/README.md)
- [Web worker tests](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/django-workers/general.md)
- [Emulating cache](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/django-workers/cache.md)

### Which was the conclusions

Should be fine read [this](./http-clients.md) first, it was the results:

Gevent:

- Stability: good
- Blocking code: it is bad, it gets worse the longer it lasts.
- Non-blocking code: it is the better option.
- Async support: no.
- Best HTTP sync client: requests, HTTPX performs bad, maybe its performance is degraded by the patch.
- Best HTTP async client: not compatible.

Uvicorn:

- Statibility: good
- Blocking code: Good.
- Non-blocking code: regular.
- Async support: yes.
- Best HTTP sync client: requests, HTTPX performs bad, maybe its performance is degraded by the patch.
- Best HTTP async client: AIOHTTP is good.

Hypercorn + Asyncio:

- Stability: bad, I could configure it properly.
- Blocking code: weak.
- Non-blocking code: regular.
- Async support: yes.
- Best HTTP sync client: requests, HTTPX performs bad, maybe its performance is degraded by the patch.
- Best HTTP async client: AIOHTTP is good.

Hypercorn + Evloop:

- Stability: bad, I could configure it properly.
- Blocking code: Best performance, with fails.
- Non-blocking code: regular.
- Async support: yes.
- Best HTTP sync client: requests, HTTPX perform bad, maybe its performance is degraded by the patch.
- Best HTTP async client: AIOHTTP is good.

Hypercorn + Trio:

- Stability: no supported yet

#### Notes

- RPS are requests per second.
- Requests do not support asynchronous code, so you cannot use wait with it.

#### Making requests within the web worker

| Library              | Gevent       | Uvicorn     | Hypercorn + Asyncio | Hypercorn + Evloop |
| -------------------- | ------------ | ----------- | ------------------- | ------------------ |
| Sync JSON            | 30913.89 RPS | 4061.19 RPS | 3753.90 RPS         | 4929.08 RPS        |
| Async JSON           |              | 3464.25 RPS | 3270.73 RPS         | 4533.80 RPS        |
| Sync query JSON      | 11498.22 RPS | 1845.01 RPS | 1691.03 RPS         | 1969.74 RPS        |
| Async query JSON     |              | 1997.32 RPS | 1565.80 RPS         | 2148.56 RPS        |
| Sync query HTML      | 7113.50 RPS  | 1590.24 RPS | 1189.28 RPS         | 1577.94 RPS        |
| Async query HTML     |              | 1749.29 RPS | 1382.19 RPS         | 1792.08 RPS        |
| Sync blocking 1s     | 1861.80 RPS  | 1819.99 RPS | 1747.01 RPS         | 1769.52 RPS        |
| Async blocking 1s    |              | 1805.06 RPS | 1676.20 RPS         | 1712.17 RPS        |
| Sync blocking 3s     | 635.14 RPS   | 631.95 RPS  | 585.55 RPS          | 578.60 RPS         |
| Async blocking 3s    |              | 1592.22 RPS | 1476.54 RPS         | 1395.52 RPS        |
| Sync blocking 10s    | 181.38 RPS   | 181.37 RPS  | 181.43 RPS          | 152.51 RPS         |
| Async blocking 10s   |              | 90.72 RPS   | 37.97 RPS           | 29.12 RPS          |
| Sync Brotli          | 414.45 RPS   | 295.72 RPS  | 314.35 RPS          | 324.34 RPS         |
| Async Brotli         |              | 158.04 RPS  | 142.45 RPS          | 193.18 RPS         |
| Sync Request         | 38.50 RPS    | 25.08 RPS   | 22.04 RPS           | 16.01 RPS          |
| Async Request        |              | 0.00 RPS    | 0.00 RPS            | 0.00 RPS           |
| Sync HTTPX           | 0.50 RPS     | 0.00 RPS    | 0.00 RPS            | 0.00 RPS           |
| Async HTTPX          |              | 42.81 RPS   | 17.74 RPS           | 17.42 RPS          |
| Async AIOHTTP        |              | 35.07 RPS   | 23.40 RPS           | 45.29 RPS          |
| Sync Fake Redis hit  | 26658.00 RPS | 5654.22 RPS | 3251.49 RPS         | 4327.30 RPS        |
| Async Fake Redis hit |              | 6295.06 RPS | 3735.66 RPS         | 4035.76 RPS        |
| Sync Fake Redis set  | 9669.09 RPS  | 4366.79 RPS | 3236.40 RPS         | 3676.91 RPS        |
| Async Fake Redis set |              | 3806.02 RPS | 3399.52 RPS         | 3713.74 RPS        |
