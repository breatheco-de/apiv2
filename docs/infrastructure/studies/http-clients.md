# Better HTTP client

This article is based fundamentally on which option is better in efficiency and features, we are covering tree libraries because them was a popular choice by the community.

## Collected HTTP clients

### Request

[Requests](https://pypi.org/project/requests/) is a library that focuses on a synchronous way to write code, it is the most popular choice but lacks asynchronous compatibility.

### HTTPX

[HTTPX](https://pypi.org/project/httpx/) is a library that is synchronous and asynchronous, this library is the most versatile of them, and it supports HTTP2.

### AIOHTTP

[AIOHTTP](https://pypi.org/project/aiohttp/) is a library focused on asynchronous code, and many people claim that it is a faster library.

## Source of Truth

To see how these libraries perform about each other I wrote `Requests vs HTTPX vs AIOHTTP`, and then I needed to see how should impact the blocking code to the web worker, I wrote `Gevent vs Uvicorn vs Hypercorn` to cover this purpose

### Source

- [Requests vs HTTPX vs AIOHTTP](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/http)
- [Gevent vs Uvicorn vs Hypercorn](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/django-workers/)

### Result

- [Requests vs HTTPX vs AIOHTTP, 1000 requests](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/http/1000-requests.md)
- [Requests vs HTTPX vs AIOHTTP, 20 urls](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/http/20-urls.md)
- [Effects of using blocking code](https://github.com/breatheco-de/apiv2/blob/development/benchmarks/blocking.md)

### Which was the conclusions

Requests and AIOHTTP were the most stable over all web workers, I could not get HTTPX to work with those settings. HTTPX is theoretically better than Requests but I cannot replicate it. AIOHTTP was from 4 to 10 times faster than Requests, and it does not block the execution flow. You can follow this topic [here](./django-workers.md).

#### Notes

- RPS are requests per second.
- Requests do not support asynchronous code, so you cannot use wait with it.
- All requests were tested within 22 seconds.

#### Visit https://www.google.com 1000 times

| Library  | Sync   | Async  |
| -------- | ------ | ------ |
| Requests | 48.43s |        |
| HTTPX    | 19.02s | 37.86s |
| AIOHTTP  |        | 13.03s |

#### Visit 20 sites

| Library  | Sync  | Async |
| -------- | ----- | ----- |
| Requests | 7.15s |       |
| HTTPX    | 4.37s | 2.28s |
| AIOHTTP  |       | 0.72s |

#### Making requests within the web worker

| Library        | Gevent    | Uvicorn   | Hypercorn + Asyncio | Hypercorn + Evloop |
| -------------- | --------- | --------- | ------------------- | ------------------ |
| Sync Requests  | 40.12 RPS | 27.72 RPS | 16.47 RPS           | 16.20 RPS          |
| Async Requests |           | 0.00 RPS  | 0.00 RPS            | 0.00 RPS           |
| Sync HTTPX     | 0.41 RPS  | 3.58 RPS  | 0.00 RPS            | 0.00 RPS           |
| Async HTTPX    |           | 0.00 RPS  | 21.83 RPS           | 18.61 RPS          |
| Async AIOHTTP  |           | 24.18 RPS | 18.73 RPS           | 37.26 RPS          |
