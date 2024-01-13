# Django Workers
## WSGI Gunicorn Gevent

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   230.04ms  432.02ms   2.00s    84.42%
    Req/Sec     1.72k     1.12k   13.84k    77.85%
  311648 requests in 10.09s, 91.25MB read
  Socket errors: connect 0, read 189, write 0, timeout 2784
Requests/sec:  30875.49
Transfer/sec:      9.04MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   103.22ms  256.58ms   1.96s    87.50%
    Req/Sec     1.62k   566.69     4.01k    69.57%
  118588 requests in 10.10s, 141.14MB read
  Socket errors: connect 0, read 0, write 0, timeout 213
Requests/sec:  11744.67
Transfer/sec:     13.98MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    71.11ms  241.51ms   2.00s    91.56%
    Req/Sec   788.17    708.15     4.10k    79.00%
  68458 requests in 10.08s, 202.45MB read
  Socket errors: connect 0, read 0, write 0, timeout 177
Requests/sec:   6790.23
Transfer/sec:     20.08MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    68.27ms   1.38s    96.02%
    Req/Sec   100.76     97.81   470.00     85.11%
  16949 requests in 10.09s, 4.74MB read
Requests/sec:   1679.07
Transfer/sec:    480.46KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   248.71    383.08     1.00k    75.61%
  6000 requests in 10.10s, 1.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    594.34
Transfer/sec:    170.06KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    76.88    140.52   410.00     76.47%
  552 requests in 10.10s, 158.76KB read
  Socket errors: connect 0, read 0, write 0, timeout 552
Requests/sec:     54.66
Transfer/sec:     15.72KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    49.12ms   60.22ms   1.81s    99.60%
    Req/Sec    64.88     39.55   220.00     60.30%
  4355 requests in 10.10s, 27.94MB read
  Socket errors: connect 0, read 0, write 0, timeout 80
Requests/sec:    431.36
Transfer/sec:      2.77MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     6.45      7.51    50.00     89.52%
  318 requests in 10.09s, 7.76MB read
  Socket errors: connect 0, read 0, write 0, timeout 318
Requests/sec:     31.51
Transfer/sec:    787.59KB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.64s    42.64ms   1.68s    83.33%
    Req/Sec     2.40      3.79    20.00     86.90%
  99 requests in 10.09s, 2.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 93
Requests/sec:      9.81
Transfer/sec:    245.19KB
```

## ASGI Gunicorn Uvicorn

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   474.17ms  159.60ms   1.53s    78.88%
    Req/Sec   215.22     80.23   720.00     76.62%
  41519 requests in 10.10s, 11.17MB read
Requests/sec:   4111.38
Transfer/sec:      1.11MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   469.90ms  138.30ms   1.30s    75.95%
    Req/Sec   214.22     64.14   646.00     72.29%
  41677 requests in 10.10s, 11.21MB read
Requests/sec:   4125.32
Transfer/sec:      1.11MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   923.25ms  203.36ms   2.00s    85.04%
    Req/Sec   108.87     53.88   600.00     73.13%
  20576 requests in 10.07s, 24.00MB read
  Socket errors: connect 0, read 0, write 0, timeout 94
Requests/sec:   2042.73
Transfer/sec:      2.38MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   891.34ms  193.51ms   2.00s    86.80%
    Req/Sec   111.51     44.23   540.00     75.30%
  21420 requests in 10.10s, 24.98MB read
  Socket errors: connect 0, read 0, write 0, timeout 48
Requests/sec:   2121.20
Transfer/sec:      2.47MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   264.89ms   2.00s    77.82%
    Req/Sec    89.41     40.33   383.00     72.03%
  16734 requests in 10.10s, 49.09MB read
  Socket errors: connect 0, read 0, write 0, timeout 671
Requests/sec:   1656.66
Transfer/sec:      4.86MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   984.82ms  200.16ms   2.00s    83.79%
    Req/Sec   101.18     46.55   500.00     72.48%
  19124 requests in 10.10s, 56.10MB read
  Socket errors: connect 0, read 0, write 0, timeout 223
Requests/sec:   1893.47
Transfer/sec:      5.55MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   100.82ms   1.48s    88.48%
    Req/Sec   144.74    143.68     0.86k    84.59%
  17794 requests in 10.10s, 4.55MB read
Requests/sec:   1762.12
Transfer/sec:    461.18KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   222.76ms   1.97s    88.22%
    Req/Sec   134.75    121.54   720.00     73.77%
  16980 requests in 10.10s, 4.34MB read
Requests/sec:   1681.70
Transfer/sec:    440.13KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   172.21    177.55   797.00     84.98%
  6000 requests in 10.10s, 1.53MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    594.10
Transfer/sec:    155.49KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    62.75ms   1.27s    81.24%
    Req/Sec   128.81    116.82   646.00     73.60%
  13442 requests in 10.10s, 3.44MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1331.13
Transfer/sec:    348.38KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     2.00      1.15     3.00    100.00%
  97 requests in 10.10s, 25.39KB read
  Socket errors: connect 0, read 0, write 0, timeout 97
Requests/sec:      9.61
Transfer/sec:      2.51KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     1.00      1.00     2.00    100.00%
  42 requests in 10.09s, 10.99KB read
  Socket errors: connect 0, read 47, write 0, timeout 42
Requests/sec:      4.16
Transfer/sec:      1.09KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.62s   289.60ms   2.00s    65.43%
    Req/Sec    18.76     15.12   100.00     80.56%
  2531 requests in 10.11s, 16.18MB read
  Socket errors: connect 0, read 0, write 0, timeout 2262
Requests/sec:    250.27
Transfer/sec:      1.60MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.90s    92.22ms   2.00s    55.56%
    Req/Sec    52.69     46.98   310.00     67.93%
  2055 requests in 10.09s, 13.13MB read
  Socket errors: connect 0, read 0, write 0, timeout 2046
Requests/sec:    203.64
Transfer/sec:      1.30MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s   237.17ms   1.61s    75.76%
    Req/Sec    15.64     17.31    90.00     87.50%
  248 requests in 10.09s, 6.05MB read
  Socket errors: connect 0, read 0, write 0, timeout 149
Requests/sec:     24.57
Transfer/sec:    613.67KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
  Socket errors: connect 0, read 9, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.10s   108.19ms   1.41s    73.91%
    Req/Sec     5.20      7.58    30.00     91.00%
  130 requests in 10.03s, 3.17MB read
  Socket errors: connect 0, read 79, write 0, timeout 107
Requests/sec:     12.96
Transfer/sec:    323.61KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
  Socket errors: connect 0, read 381, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.38s   312.49ms   1.91s    52.24%
    Req/Sec     8.58      8.01    50.00     82.75%
  556 requests in 10.10s, 13.56MB read
  Socket errors: connect 0, read 0, write 0, timeout 489
Requests/sec:     55.06
Transfer/sec:      1.34MB
```

## ASGI Hypercorn Asyncio

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   414.64ms  314.93ms   1.51s    71.19%
    Req/Sec   266.23    132.38   790.00     65.87%
  50568 requests in 10.09s, 13.87MB read
Requests/sec:   5009.32
Transfer/sec:      1.37MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   421.30ms  200.57ms   1.42s    69.44%
    Req/Sec   225.65    107.10   770.00     72.89%
  44711 requests in 10.10s, 12.23MB read
Requests/sec:   4426.40
Transfer/sec:      1.21MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   868.58ms  421.90ms   2.00s    63.98%
    Req/Sec    95.28     62.18   404.00     68.55%
  18511 requests in 10.10s, 21.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 806
Requests/sec:   1832.75
Transfer/sec:      2.15MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   817.83ms  380.95ms   2.00s    68.99%
    Req/Sec    97.53     66.96   500.00     70.02%
  17870 requests in 10.10s, 20.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 1154
Requests/sec:   1769.44
Transfer/sec:      2.07MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   700.95ms  454.23ms   2.00s    77.10%
    Req/Sec    85.05     52.71   434.00     67.93%
  16064 requests in 10.10s, 47.20MB read
  Socket errors: connect 0, read 0, write 0, timeout 2079
Requests/sec:   1590.43
Transfer/sec:      4.67MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   952.59ms  397.70ms   1.94s    67.17%
    Req/Sec    88.01     81.77   820.00     83.15%
  15857 requests in 10.10s, 46.58MB read
  Socket errors: connect 0, read 0, write 0, timeout 376
Requests/sec:   1570.00
Transfer/sec:      4.61MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.16s   173.69ms   2.00s    84.31%
    Req/Sec    94.79     80.34   640.00     74.10%
  15096 requests in 10.09s, 3.94MB read
  Socket errors: connect 0, read 0, write 0, timeout 97
Requests/sec:   1495.78
Transfer/sec:    399.47KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.14s   164.14ms   1.94s    89.28%
    Req/Sec   107.18    101.49   660.00     82.79%
  14345 requests in 10.10s, 3.74MB read
  Socket errors: connect 0, read 0, write 0, timeout 301
Requests/sec:   1420.22
Transfer/sec:    378.83KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   122.34    136.39   640.00     85.60%
  5492 requests in 10.08s, 1.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 5492
Requests/sec:    544.90
Transfer/sec:    144.74KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.10s   125.81ms   1.90s    95.73%
    Req/Sec   101.06    103.54   740.00     84.35%
  10183 requests in 10.10s, 2.66MB read
  Socket errors: connect 0, read 0, write 0, timeout 802
Requests/sec:   1008.67
Transfer/sec:    269.69KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 185, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.21s   477.98ms   1.99s    60.56%
    Req/Sec    27.31     28.08   272.00     87.82%
  3175 requests in 10.15s, 20.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 2460
Requests/sec:    312.72
Transfer/sec:      2.00MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   905.38ms  615.96ms   1.99s    49.54%
    Req/Sec    33.90     86.58     0.89k    93.84%
  1768 requests in 10.10s, 11.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 1441
Requests/sec:    175.13
Transfer/sec:      1.12MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.44s   553.81ms   1.97s    72.22%
    Req/Sec     4.38      5.74    30.00     93.40%
  142 requests in 10.10s, 3.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 124
  Non-2xx or 3xx responses: 9
Requests/sec:     14.06
Transfer/sec:    329.21KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 1, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     9.40     17.76    70.00     92.00%
  45 requests in 10.09s, 1.10MB read
  Socket errors: connect 0, read 61, write 0, timeout 45
Requests/sec:      4.46
Transfer/sec:    111.38KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.43s   398.10ms   1.99s    65.00%
    Req/Sec     5.63      7.45    40.00     91.34%
  323 requests in 10.02s, 7.88MB read
  Socket errors: connect 0, read 5, write 0, timeout 283
Requests/sec:     32.24
Transfer/sec:    805.30KB
```

## ASGI Hypercorn Uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   357.28ms  148.66ms   2.00s    84.00%
    Req/Sec   260.02    117.17     0.98k    73.44%
  48658 requests in 10.10s, 13.27MB read
  Socket errors: connect 0, read 0, write 0, timeout 6
Requests/sec:   4818.16
Transfer/sec:      1.31MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   238.53ms  152.99ms   1.99s    88.70%
    Req/Sec   271.78    175.51     1.17k    64.76%
  53965 requests in 10.10s, 14.72MB read
  Socket errors: connect 0, read 0, write 0, timeout 228
Requests/sec:   5342.56
Transfer/sec:      1.46MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   640.34ms  239.17ms   1.27s    66.73%
    Req/Sec   109.85     76.35   700.00     71.41%
  21245 requests in 10.10s, 24.86MB read
  Socket errors: connect 0, read 0, write 0, timeout 372
Requests/sec:   2103.20
Transfer/sec:      2.46MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   488.04ms  263.02ms   1.21s    60.88%
    Req/Sec   120.29    112.21     1.07k    89.01%
  22149 requests in 10.10s, 25.92MB read
  Socket errors: connect 0, read 0, write 0, timeout 679
Requests/sec:   2193.29
Transfer/sec:      2.57MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   575.71ms  326.08ms   1.98s    68.19%
    Req/Sec    91.80     81.99   600.00     87.97%
  17376 requests in 10.10s, 51.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 565
Requests/sec:   1720.51
Transfer/sec:      5.05MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   458.65ms  230.66ms   2.00s    65.25%
    Req/Sec   107.84     90.20   560.00     75.07%
  20081 requests in 10.09s, 58.98MB read
  Socket errors: connect 0, read 0, write 0, timeout 495
Requests/sec:   1989.24
Transfer/sec:      5.84MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    43.65ms   1.27s    81.83%
    Req/Sec   122.23    129.48   727.00     85.08%
  11284 requests in 10.10s, 2.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 399
Requests/sec:   1117.34
Transfer/sec:    296.79KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    79.08ms   1.96s    95.23%
    Req/Sec   113.37    126.74     0.95k    88.14%
  11694 requests in 10.10s, 3.03MB read
  Socket errors: connect 0, read 0, write 0, timeout 647
Requests/sec:   1158.08
Transfer/sec:    307.61KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    82.27    114.54   680.00     85.62%
  4810 requests in 10.10s, 1.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 4810
Requests/sec:    476.22
Transfer/sec:    126.50KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    74.17ms   1.95s    94.59%
    Req/Sec    87.02    119.54   727.00     89.29%
  8454 requests in 10.10s, 2.19MB read
  Socket errors: connect 0, read 0, write 0, timeout 912
Requests/sec:    837.29
Transfer/sec:    222.40KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 327, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   390.42ms   2.00s    67.34%
    Req/Sec    36.00     41.95   320.00     84.96%
  3555 requests in 10.08s, 22.74MB read
  Socket errors: connect 0, read 178, write 0, timeout 790
Requests/sec:    352.66
Transfer/sec:      2.26MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.43s   368.52ms   2.00s    73.85%
    Req/Sec    31.36     30.29   202.00     82.04%
  2064 requests in 10.09s, 13.20MB read
  Socket errors: connect 0, read 0, write 0, timeout 1651
Requests/sec:    204.66
Transfer/sec:      1.31MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.62s   184.56ms   1.98s    50.72%
    Req/Sec     4.73      8.87    60.00     90.91%
  190 requests in 10.10s, 4.63MB read
  Socket errors: connect 0, read 32, write 0, timeout 121
Requests/sec:     18.81
Transfer/sec:    469.86KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
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
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 40, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```
