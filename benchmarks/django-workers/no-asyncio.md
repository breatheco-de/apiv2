# Django Workers
## WSGI Gunicorn Gevent

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   249.40ms  422.50ms   2.00s    83.64%
    Req/Sec     1.62k   732.02     5.06k    68.19%
  313307 requests in 10.09s, 91.73MB read
  Socket errors: connect 0, read 30, write 0, timeout 2197
Requests/sec:  31060.30
Transfer/sec:      9.09MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   102.39ms  298.26ms   2.00s    89.84%
    Req/Sec     0.91k   489.39     3.58k    70.94%
  108000 requests in 10.10s, 128.54MB read
  Socket errors: connect 0, read 0, write 0, timeout 1098
Requests/sec:  10697.38
Transfer/sec:     12.73MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    71.89ms  243.10ms   1.99s    91.45%
    Req/Sec   836.40    727.80     7.16k    85.15%
  63871 requests in 10.07s, 188.89MB read
  Socket errors: connect 0, read 0, write 0, timeout 190
Requests/sec:   6344.33
Transfer/sec:     18.76MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    66.82ms   1.35s    95.50%
    Req/Sec   110.73    117.04   680.00     87.47%
  16822 requests in 10.10s, 4.70MB read
Requests/sec:   1666.24
Transfer/sec:    476.77KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   345.94    437.99     1.00k    66.88%
  8257 requests in 15.03s, 2.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 8257
Requests/sec:    549.32
Transfer/sec:    157.29KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   279.24    363.28     1.00k    75.00%
  4000 requests in 22.05s, 1.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.44
Transfer/sec:     51.92KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    52.49ms   75.05ms   1.84s    99.32%
    Req/Sec    47.17     29.57   161.00     78.76%
  4214 requests in 10.10s, 27.03MB read
  Socket errors: connect 0, read 0, write 0, timeout 82
Requests/sec:    417.21
Transfer/sec:      2.68MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   136.97ms  120.20ms 907.74ms   88.37%
    Req/Sec   827.69    329.73     2.17k    71.82%
  163666 requests in 10.10s, 45.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 111
Requests/sec:  16209.83
Transfer/sec:      4.53MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   204.94ms   17.00ms 707.09ms   95.30%
    Req/Sec   489.03    243.99     1.00k    64.32%
  97361 requests in 10.10s, 27.21MB read
Requests/sec:   9639.39
Transfer/sec:      2.69MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s   534.74ms   1.97s    57.26%
    Req/Sec     5.72      5.76    30.00     92.92%
  443 requests in 10.10s, 10.81MB read
  Socket errors: connect 0, read 0, write 0, timeout 319
Requests/sec:     43.86
Transfer/sec:      1.07MB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.83s    96.47ms   1.89s   100.00%
    Req/Sec     1.81      3.94    20.00     93.65%
  71 requests in 10.10s, 1.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 69
Requests/sec:      7.03
Transfer/sec:    175.73KB
```

## ASGI Gunicorn Uvicorn

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   401.44ms  124.32ms   1.37s    90.85%
    Req/Sec   261.94     67.90   690.00     72.53%
  49478 requests in 10.03s, 13.31MB read
Requests/sec:   4933.97
Transfer/sec:      1.33MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   420.75ms  110.82ms   1.13s    74.89%
    Req/Sec   237.53     82.74     0.86k    72.51%
  46395 requests in 10.04s, 12.48MB read
Requests/sec:   4619.16
Transfer/sec:      1.24MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   913.57ms  199.31ms   2.00s    86.34%
    Req/Sec   109.42     51.81   720.00     79.27%
  20862 requests in 10.09s, 24.33MB read
  Socket errors: connect 0, read 0, write 0, timeout 56
Requests/sec:   2067.26
Transfer/sec:      2.41MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   915.73ms  193.47ms   1.99s    86.46%
    Req/Sec   110.13     53.01   380.00     73.44%
  20723 requests in 10.10s, 24.17MB read
  Socket errors: connect 0, read 0, write 0, timeout 82
Requests/sec:   2051.98
Transfer/sec:      2.39MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   264.55ms   2.00s    75.00%
    Req/Sec    85.78     38.35   303.00     74.66%
  16057 requests in 10.04s, 47.10MB read
  Socket errors: connect 0, read 0, write 0, timeout 546
Requests/sec:   1599.37
Transfer/sec:      4.69MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s   199.92ms   2.00s    83.06%
    Req/Sec    97.36     48.42   560.00     75.68%
  18042 requests in 10.08s, 52.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 311
Requests/sec:   1789.12
Transfer/sec:      5.25MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   118.82ms   1.61s    89.55%
    Req/Sec   154.54    178.10     0.87k    85.51%
  17976 requests in 10.10s, 4.59MB read
Requests/sec:   1780.33
Transfer/sec:    465.94KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   249.32ms   2.00s    89.96%
    Req/Sec   140.02    128.90   767.00     73.25%
  16655 requests in 10.02s, 4.26MB read
  Socket errors: connect 0, read 0, write 0, timeout 364
Requests/sec:   1662.13
Transfer/sec:    435.01KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   148.19    127.67   740.00     65.37%
  8000 requests in 15.04s, 2.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 8000
Requests/sec:    531.98
Transfer/sec:    139.23KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s   184.16ms   1.92s    92.39%
    Req/Sec   119.37    101.01     0.95k    76.04%
  26358 requests in 15.09s, 6.74MB read
Requests/sec:   1746.28
Transfer/sec:    457.03KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   185.64    152.56   643.00     58.76%
  4000 requests in 22.05s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.43
Transfer/sec:     47.48KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   136.20    154.82   737.00     82.81%
  2000 requests in 22.04s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:     90.73
Transfer/sec:     23.75KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.21s   617.58ms   1.96s    55.56%
    Req/Sec    27.80     24.64   170.00     80.14%
  3507 requests in 10.11s, 22.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 3444
Requests/sec:    346.97
Transfer/sec:      2.22MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.90s   101.27ms   2.00s    75.00%
    Req/Sec    47.44     39.21   240.00     70.96%
  1808 requests in 10.10s, 11.56MB read
  Socket errors: connect 0, read 0, write 0, timeout 1804
Requests/sec:    178.92
Transfer/sec:      1.14MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   508.79ms  134.36ms   1.05s    68.91%
    Req/Sec   195.94     76.08   656.00     76.57%
  38388 requests in 10.10s, 9.81MB read
Requests/sec:   3800.81
Transfer/sec:      0.97MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   532.05ms  117.13ms   1.37s    78.55%
    Req/Sec   188.06     61.88   680.00     72.71%
  36698 requests in 10.10s, 9.38MB read
Requests/sec:   3634.95
Transfer/sec:      0.93MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   552.88ms  114.66ms   1.20s    68.19%
    Req/Sec   182.88     82.36   770.00     74.75%
  35198 requests in 10.08s, 9.00MB read
Requests/sec:   3491.90
Transfer/sec:      0.89MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   540.96ms  133.49ms   1.15s    69.82%
    Req/Sec   188.67     72.61   570.00     72.34%
  35959 requests in 10.10s, 9.19MB read
Requests/sec:   3560.81
Transfer/sec:      0.91MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   256.06ms   1.99s    77.82%
    Req/Sec     6.17      7.99    50.00     87.00%
  394 requests in 10.09s, 9.61MB read
  Socket errors: connect 0, read 0, write 0, timeout 119
Requests/sec:     39.03
Transfer/sec:      0.95MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 57, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.21s   289.34ms   2.00s    68.48%
    Req/Sec     4.79      6.24    40.00     94.80%
  335 requests in 10.09s, 8.17MB read
  Socket errors: connect 0, read 176, write 0, timeout 151
Requests/sec:     33.19
Transfer/sec:    828.88KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.25      0.50     1.00     75.00%
  6 requests in 10.03s, 149.84KB read
  Socket errors: connect 0, read 205, write 0, timeout 6
Requests/sec:      0.60
Transfer/sec:     14.94KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s   457.44ms   1.95s    63.83%
    Req/Sec     6.13      5.89    30.00     80.26%
  386 requests in 10.10s, 9.41MB read
  Socket errors: connect 0, read 0, write 0, timeout 339
Requests/sec:     38.22
Transfer/sec:      0.93MB
```

## ASGI Hypercorn Uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   486.26ms  187.50ms   1.45s    70.24%
    Req/Sec   178.95     85.53   656.00     73.86%
  34059 requests in 10.05s, 9.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 233
Requests/sec:   3390.18
Transfer/sec:      0.92MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   337.76ms  184.46ms   1.82s    85.53%
    Req/Sec   184.57    137.55     1.11k    69.44%
  35004 requests in 10.10s, 9.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 207
Requests/sec:   3466.09
Transfer/sec:      0.95MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   442.23ms  205.87ms   1.03s    61.30%
    Req/Sec   112.25     79.50   623.00     72.24%
  22115 requests in 10.10s, 25.88MB read
  Socket errors: connect 0, read 0, write 0, timeout 378
Requests/sec:   2190.09
Transfer/sec:      2.56MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   285.29ms  127.22ms 678.70ms   67.56%
    Req/Sec   136.84    139.48   811.00     84.46%
  24669 requests in 10.05s, 28.87MB read
  Socket errors: connect 0, read 0, write 0, timeout 328
Requests/sec:   2455.44
Transfer/sec:      2.87MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   727.52ms  388.55ms   2.00s    69.03%
    Req/Sec    85.21     58.14   500.00     77.85%
  16657 requests in 10.10s, 48.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 609
Requests/sec:   1649.20
Transfer/sec:      4.84MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   528.87ms  299.73ms   2.00s    73.70%
    Req/Sec    99.96     88.99   630.00     78.44%
  19061 requests in 10.10s, 55.99MB read
  Socket errors: connect 0, read 0, write 0, timeout 361
Requests/sec:   1887.43
Transfer/sec:      5.54MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s    65.28ms   1.40s    91.77%
    Req/Sec    93.98    101.18   680.00     84.37%
  9489 requests in 10.10s, 2.46MB read
  Socket errors: connect 0, read 92, write 0, timeout 0
Requests/sec:    939.54
Transfer/sec:    249.57KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.08s   149.14ms   2.00s    93.11%
    Req/Sec    90.98     90.25   595.00     85.86%
  12032 requests in 10.09s, 3.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 589
Requests/sec:   1192.30
Transfer/sec:    316.70KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   107.88    152.09   790.00     84.80%
  7749 requests in 15.04s, 2.01MB read
  Socket errors: connect 0, read 0, write 0, timeout 7749
Requests/sec:    515.26
Transfer/sec:    136.86KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    85.00ms   1.88s    97.82%
    Req/Sec   104.24    101.87   787.00     83.45%
  17724 requests in 15.10s, 4.60MB read
  Socket errors: connect 0, read 0, write 0, timeout 1181
Requests/sec:   1173.86
Transfer/sec:    311.81KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.05s, 0.00B read
  Socket errors: connect 0, read 3572, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.05s, 0.00B read
  Socket errors: connect 0, read 733, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.58s   410.06ms   1.99s    80.77%
    Req/Sec    24.82     24.60   220.00     86.90%
  3329 requests in 10.11s, 21.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 3147
Requests/sec:    329.41
Transfer/sec:      2.11MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.61s   313.26ms   2.00s    67.58%
    Req/Sec    41.66     39.73   250.00     84.29%
  3454 requests in 10.09s, 22.09MB read
  Socket errors: connect 0, read 49, write 0, timeout 1378
Requests/sec:    342.26
Transfer/sec:      2.19MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   284.98ms   84.66ms 582.79ms   69.33%
    Req/Sec   228.51    140.28   838.00     65.08%
  44205 requests in 10.10s, 11.47MB read
  Socket errors: connect 0, read 58, write 0, timeout 0
Requests/sec:   4376.05
Transfer/sec:      1.14MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   459.59ms  171.23ms   1.31s    76.33%
    Req/Sec   185.61     92.38   838.00     76.57%
  36829 requests in 10.10s, 9.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 91
Requests/sec:   3648.20
Transfer/sec:      0.95MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   486.44ms  134.03ms   1.61s    74.96%
    Req/Sec   173.55     90.54   680.00     71.12%
  33551 requests in 10.10s, 8.70MB read
  Socket errors: connect 0, read 0, write 0, timeout 206
Requests/sec:   3322.25
Transfer/sec:      0.86MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   482.82ms  147.24ms   1.62s    72.08%
    Req/Sec   179.10     98.52   690.00     68.60%
  33722 requests in 10.10s, 8.75MB read
  Socket errors: connect 0, read 0, write 0, timeout 16
Requests/sec:   3338.87
Transfer/sec:      0.87MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.20s   326.71ms   2.00s    65.78%
    Req/Sec     5.81      8.29    60.00     91.02%
  350 requests in 10.10s, 8.54MB read
  Socket errors: connect 0, read 0, write 0, timeout 163
Requests/sec:     34.66
Transfer/sec:    865.68KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.53s   147.27ms   1.78s    75.68%
    Req/Sec     3.36      5.16    30.00     82.08%
  139 requests in 10.09s, 3.39MB read
  Socket errors: connect 0, read 0, write 0, timeout 102
Requests/sec:     13.77
Transfer/sec:    344.03KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     5.30      6.86    20.00     90.00%
  13 requests in 10.10s, 324.71KB read
  Socket errors: connect 0, read 0, write 0, timeout 13
Requests/sec:      1.29
Transfer/sec:     32.16KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.20s   405.49ms   1.97s    65.15%
    Req/Sec     6.38      6.93    40.00     91.58%
  374 requests in 10.10s, 9.12MB read
  Socket errors: connect 0, read 66, write 0, timeout 308
Requests/sec:     37.03
Transfer/sec:      0.90MB
```

## Granian uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   402.01ms  201.92ms   1.27s    75.09%
    Req/Sec   258.92     85.94   525.00     68.89%
  49132 requests in 10.03s, 13.21MB read
Requests/sec:   4897.59
Transfer/sec:      1.32MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   389.49ms  228.40ms   1.36s    61.01%
    Req/Sec   259.19    123.79     0.87k    68.09%
  50987 requests in 10.09s, 13.71MB read
Requests/sec:   5051.78
Transfer/sec:      1.36MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   658.76ms  393.35ms   2.00s    71.33%
    Req/Sec   148.23     75.41   450.00     69.39%
  29086 requests in 10.06s, 33.92MB read
  Socket errors: connect 0, read 0, write 0, timeout 234
Requests/sec:   2892.49
Transfer/sec:      3.37MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   833.85ms  527.26ms   2.00s    59.34%
    Req/Sec   113.92     71.93   393.00     69.34%
  21832 requests in 10.03s, 25.46MB read
  Socket errors: connect 0, read 0, write 0, timeout 476
Requests/sec:   2176.02
Transfer/sec:      2.54MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   861.54ms  459.47ms   2.00s    65.55%
    Req/Sec    76.63     46.46   350.00     68.02%
  14276 requests in 10.10s, 41.88MB read
  Socket errors: connect 0, read 0, write 0, timeout 2150
Requests/sec:   1413.39
Transfer/sec:      4.15MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   800.86ms  512.04ms   2.00s    57.12%
    Req/Sec    86.34     60.84   424.00     72.19%
  16102 requests in 10.10s, 47.24MB read
  Socket errors: connect 0, read 0, write 0, timeout 2332
Requests/sec:   1594.93
Transfer/sec:      4.68MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.23s   215.28ms   2.00s    72.97%
    Req/Sec    90.07     70.00   570.00     70.45%
  15113 requests in 10.10s, 3.86MB read
  Socket errors: connect 0, read 0, write 0, timeout 154
Requests/sec:   1496.43
Transfer/sec:    391.64KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   159.96ms   1.74s    65.85%
    Req/Sec    93.70     70.83   490.00     74.05%
  15538 requests in 10.10s, 3.97MB read
Requests/sec:   1538.52
Transfer/sec:    402.66KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   114.10    108.77   630.00     75.37%
  8000 requests in 15.05s, 2.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 8000
Requests/sec:    531.72
Transfer/sec:    139.16KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.21s   140.76ms   1.64s    62.74%
    Req/Sec    90.31     61.42   480.00     72.72%
  23945 requests in 15.03s, 6.12MB read
Requests/sec:   1592.90
Transfer/sec:    416.89KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   166.41    141.79   530.00     56.54%
  4000 requests in 22.07s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.27
Transfer/sec:     47.44KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   151.41    125.43   515.00     59.68%
  4000 requests in 22.05s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.37
Transfer/sec:     47.47KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.39s   519.64ms   2.00s    70.43%
    Req/Sec    22.06     20.05   171.00     85.13%
  3200 requests in 10.10s, 20.45MB read
  Socket errors: connect 0, read 0, write 0, timeout 2970
Requests/sec:    316.73
Transfer/sec:      2.02MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.24s   467.92ms   1.99s    60.86%
    Req/Sec    34.84     66.90   570.00     93.20%
  1357 requests in 10.10s, 8.67MB read
  Socket errors: connect 0, read 0, write 0, timeout 892
Requests/sec:    134.37
Transfer/sec:      0.86MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   544.94ms  404.17ms   2.00s    79.32%
    Req/Sec   171.76     79.76   595.00     68.64%
  33958 requests in 10.05s, 8.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 578
Requests/sec:   3379.86
Transfer/sec:      0.86MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   535.39ms  333.54ms   1.99s    72.46%
    Req/Sec   189.20     92.82   560.00     68.88%
  37111 requests in 10.10s, 9.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 311
Requests/sec:   3674.59
Transfer/sec:      0.94MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   588.77ms  240.31ms   1.83s    69.71%
    Req/Sec   171.55     81.60   555.00     73.30%
  33184 requests in 10.10s, 8.48MB read
Requests/sec:   3286.02
Transfer/sec:    860.01KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   580.36ms  245.80ms   1.46s    73.91%
    Req/Sec   171.86     88.08   590.00     67.84%
  33288 requests in 10.10s, 8.51MB read
Requests/sec:   3295.99
Transfer/sec:    862.62KB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   433.58ms   2.00s    75.58%
    Req/Sec     5.17      6.28    30.00     92.11%
  346 requests in 10.10s, 8.44MB read
  Socket errors: connect 0, read 0, write 0, timeout 174
Requests/sec:     34.26
Transfer/sec:    855.68KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    15.86     17.85    50.00     85.71%
  24 requests in 10.10s, 599.37KB read
  Socket errors: connect 0, read 0, write 0, timeout 24
Requests/sec:      2.38
Transfer/sec:     59.34KB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s   118.60ms   1.38s    60.56%
    Req/Sec     5.09      6.95    30.00     90.80%
  110 requests in 10.10s, 2.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 39
Requests/sec:     10.89
Transfer/sec:    272.02KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   956.48ms  365.76ms   1.97s    75.84%
    Req/Sec     3.83      4.38    20.00     75.83%
  233 requests in 10.10s, 5.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 55
Requests/sec:     23.08
Transfer/sec:    576.35KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   300.60ms   1.95s    92.31%
    Req/Sec     3.34      4.23    20.00     79.02%
  153 requests in 10.03s, 3.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 140
Requests/sec:     15.26
Transfer/sec:    381.09KB
```

## Daphne

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.31s   405.55ms   2.00s    51.44%
    Req/Sec    37.33     43.16   252.00     88.42%
  2818 requests in 10.10s, 671.48KB read
  Socket errors: connect 0, read 0, write 0, timeout 1673
Requests/sec:    279.07
Transfer/sec:     66.50KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   969.54ms  548.47ms   1.99s    60.49%
    Req/Sec    49.31     64.16   424.00     88.27%
  3268 requests in 10.10s, 778.70KB read
  Socket errors: connect 0, read 0, write 0, timeout 1405
Requests/sec:    323.61
Transfer/sec:     77.11KB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.37s   381.89ms   1.96s    77.83%
    Req/Sec    37.61     48.02   330.00     86.98%
  2668 requests in 10.10s, 3.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 20
Requests/sec:    264.17
Transfer/sec:    305.71KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s   558.55ms   1.99s    61.37%
    Req/Sec    41.25     64.10   440.00     90.05%
  2412 requests in 10.10s, 2.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 1335
Requests/sec:    238.81
Transfer/sec:    276.35KB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.34s   507.33ms   1.99s    62.17%
    Req/Sec    29.73     50.70   470.00     90.74%
  2044 requests in 10.10s, 5.92MB read
  Socket errors: connect 0, read 0, write 0, timeout 204
Requests/sec:    202.36
Transfer/sec:    600.36KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   533.86ms   2.00s    69.61%
    Req/Sec    43.19     62.88   545.00     88.44%
  2065 requests in 10.10s, 5.98MB read
  Socket errors: connect 0, read 0, write 0, timeout 966
Requests/sec:    204.45
Transfer/sec:    606.57KB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.49s   190.98ms   1.95s    71.69%
    Req/Sec    47.74     66.41   470.00     89.25%
  3059 requests in 10.10s, 687.08KB read
Requests/sec:    302.88
Transfer/sec:     68.03KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   144.66ms   1.80s    71.15%
    Req/Sec    41.54     61.47   420.00     88.32%
  2521 requests in 10.10s, 566.24KB read
  Socket errors: connect 0, read 0, write 0, timeout 348
Requests/sec:    249.61
Transfer/sec:     56.06KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    36.33     50.69   404.00     89.95%
  3162 requests in 15.10s, 710.21KB read
  Socket errors: connect 0, read 0, write 0, timeout 3162
Requests/sec:    209.42
Transfer/sec:     47.04KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.74s   199.61ms   1.97s    66.45%
    Req/Sec    39.80     56.05   363.00     88.92%
  3425 requests in 15.03s, 769.29KB read
  Socket errors: connect 0, read 0, write 0, timeout 3112
Requests/sec:    227.92
Transfer/sec:     51.19KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    40.22     55.40   373.00     86.76%
  2253 requests in 22.04s, 611.91KB read
  Socket errors: connect 0, read 0, write 0, timeout 2253
  Non-2xx or 3xx responses: 293
Requests/sec:    102.23
Transfer/sec:     27.76KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    24.61     54.85   270.00     90.24%
  423 requests in 22.04s, 113.80KB read
  Socket errors: connect 0, read 27, write 0, timeout 423
  Non-2xx or 3xx responses: 52
Requests/sec:     19.19
Transfer/sec:      5.16KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.60s   266.40ms   1.99s    54.49%
    Req/Sec    36.59     51.90   404.00     87.82%
  2098 requests in 10.05s, 13.33MB read
  Socket errors: connect 0, read 0, write 0, timeout 1430
Requests/sec:    208.67
Transfer/sec:      1.33MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    32.62     62.62   232.00     87.50%
  241 requests in 10.09s, 1.53MB read
  Socket errors: connect 0, read 0, write 0, timeout 241
Requests/sec:     23.88
Transfer/sec:    155.41KB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   472.15ms   2.00s    53.89%
    Req/Sec    37.09     51.22   460.00     87.99%
  3465 requests in 10.10s, 778.27KB read
  Socket errors: connect 0, read 0, write 0, timeout 1179
Requests/sec:    343.09
Transfer/sec:     77.06KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.27s   484.61ms   1.91s    70.80%
    Req/Sec    39.64     46.00   260.00     86.34%
  3563 requests in 10.10s, 800.28KB read
  Socket errors: connect 0, read 0, write 0, timeout 18
Requests/sec:    352.81
Transfer/sec:     79.25KB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   845.17ms  309.53ms   1.39s    61.57%
    Req/Sec    37.56     47.96   470.00     88.61%
  3599 requests in 10.10s, 808.37KB read
Requests/sec:    356.33
Transfer/sec:     80.04KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   473.71ms   1.99s    70.07%
    Req/Sec    46.83     69.80   454.00     91.70%
  3569 requests in 10.10s, 801.63KB read
  Socket errors: connect 0, read 0, write 0, timeout 1541
Requests/sec:    353.39
Transfer/sec:     79.37KB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.29s   326.68ms   2.00s    61.86%
    Req/Sec     5.85      7.64    40.00     88.61%
  337 requests in 10.10s, 8.21MB read
  Socket errors: connect 0, read 0, write 0, timeout 143
Requests/sec:     33.37
Transfer/sec:    832.18KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.57s   282.60ms   1.95s    42.86%
    Req/Sec     5.60      7.90    40.00     91.38%
  165 requests in 10.10s, 4.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 151
Requests/sec:     16.34
Transfer/sec:    407.53KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.50s   404.32ms   2.00s    58.41%
    Req/Sec    11.33     12.16    60.00     88.07%
  548 requests in 10.10s, 13.34MB read
  Socket errors: connect 0, read 0, write 0, timeout 435
Requests/sec:     54.27
Transfer/sec:      1.32MB
```
