# Django Workers
## WSGI Gunicorn Gevent

### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    84.83ms   71.62ms 570.10ms   89.29%
    Req/Sec     1.37k   318.64     2.91k    78.31%
  269272 requests in 10.10s, 75.24MB read
Requests/sec:  26658.00
Transfer/sec:      7.45MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   203.62ms    7.11ms 284.97ms   93.45%
    Req/Sec   491.36    269.57     1.00k    57.22%
  97651 requests in 10.10s, 27.29MB read
Requests/sec:   9669.09
Transfer/sec:      2.70MB
```

## ASGI Gunicorn Uvicorn

### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   350.14ms  107.39ms   1.20s    92.03%
    Req/Sec   303.02    100.66     0.95k    75.53%
  57096 requests in 10.10s, 14.59MB read
Requests/sec:   5654.22
Transfer/sec:      1.45MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   310.95ms   64.78ms 913.33ms   78.03%
    Req/Sec   322.48     77.76   830.00     72.82%
  63585 requests in 10.10s, 16.25MB read
Requests/sec:   6295.06
Transfer/sec:      1.61MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   443.85ms  113.02ms 874.80ms   66.25%
    Req/Sec   223.48     93.00     0.93k    73.30%
  44025 requests in 10.08s, 11.25MB read
Requests/sec:   4366.79
Transfer/sec:      1.12MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   509.17ms  122.96ms   1.16s    71.18%
    Req/Sec   200.55     73.77   474.00     71.11%
  38441 requests in 10.10s, 9.82MB read
Requests/sec:   3806.02
Transfer/sec:      0.97MB
```

## ASGI Hypercorn Asyncio

### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   561.19ms  206.28ms   1.22s    67.81%
    Req/Sec   174.38    103.13   790.00     68.70%
  32840 requests in 10.10s, 8.56MB read
Requests/sec:   3251.49
Transfer/sec:    867.71KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   504.15ms  343.27ms   2.00s    81.93%
    Req/Sec   191.77     91.31   515.00     69.86%
  37721 requests in 10.10s, 9.83MB read
  Socket errors: connect 0, read 0, write 0, timeout 317
Requests/sec:   3735.66
Transfer/sec:      0.97MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   581.85ms  264.72ms   1.34s    60.03%
    Req/Sec   169.03     86.41   580.00     68.16%
  32684 requests in 10.10s, 8.51MB read
Requests/sec:   3236.40
Transfer/sec:    863.38KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   511.62ms  158.88ms   1.02s    65.80%
    Req/Sec   182.92     75.30   752.00     72.11%
  34097 requests in 10.03s, 8.88MB read
Requests/sec:   3399.52
Transfer/sec:      0.89MB
```

## ASGI Hypercorn Uvloop

### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   397.69ms  152.88ms   2.00s    69.43%
    Req/Sec   234.03    132.59     1.11k    81.87%
  43684 requests in 10.09s, 11.33MB read
  Socket errors: connect 0, read 0, write 0, timeout 177
Requests/sec:   4327.30
Transfer/sec:      1.12MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   373.89ms  146.82ms   1.31s    76.65%
    Req/Sec   206.87    123.55     1.17k    77.37%
  40763 requests in 10.10s, 10.57MB read
  Socket errors: connect 0, read 0, write 0, timeout 322
Requests/sec:   4035.76
Transfer/sec:      1.05MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   467.51ms  127.94ms   1.56s    79.18%
    Req/Sec   191.38     89.23   757.00     73.48%
  37141 requests in 10.10s, 9.63MB read
  Socket errors: connect 0, read 0, write 0, timeout 28
Requests/sec:   3676.91
Transfer/sec:      0.95MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   441.99ms  123.13ms   2.00s    76.47%
    Req/Sec   199.21     87.88   610.00     71.18%
  37508 requests in 10.10s, 9.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 93
Requests/sec:   3713.74
Transfer/sec:      0.96MB
```
