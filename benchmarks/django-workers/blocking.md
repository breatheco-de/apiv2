# Django Workers
## WSGI Gunicorn Gevent
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    86.40ms   1.55s    95.80%
    Req/Sec   147.86    148.95   656.00     80.70%
  42086 requests in 22.10s, 11.76MB read
Requests/sec:   1904.26
Transfer/sec:    544.87KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   275.66    370.69     1.00k    74.19%
  14000 requests in 22.10s, 3.91MB read
  Socket errors: connect 0, read 0, write 0, timeout 14000
Requests/sec:    633.45
Transfer/sec:    181.25KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   119.42    189.51   680.00     84.93%
  4000 requests in 22.10s, 1.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.02
Transfer/sec:     51.80KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.58s   218.87ms   1.97s    57.50%
    Req/Sec     5.46      6.08    40.00     92.07%
  885 requests in 22.06s, 21.44MB read
  Socket errors: connect 0, read 0, write 0, timeout 845
  Non-2xx or 3xx responses: 7
Requests/sec:     40.12
Transfer/sec:      0.97MB
```

### HTTPX
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.93s    11.08ms   1.94s   100.00%
    Req/Sec     1.62      3.54    10.00     87.50%
  9 requests in 22.05s, 224.98KB read
  Socket errors: connect 0, read 0, write 0, timeout 7
Requests/sec:      0.41
Transfer/sec:     10.20KB
```

## ASGI Gunicorn Uvicorn
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   135.14ms   1.73s    94.01%
    Req/Sec   114.43    100.06     0.87k    76.84%
  40506 requests in 22.03s, 10.35MB read
Requests/sec:   1839.06
Transfer/sec:    481.32KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s   102.55ms   2.00s    98.49%
    Req/Sec   134.69    137.14     0.94k    87.37%
  39871 requests in 22.09s, 10.19MB read
  Socket errors: connect 0, read 0, write 0, timeout 1568
Requests/sec:   1804.77
Transfer/sec:    472.34KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   160.39    147.09     0.91k    65.76%
  14000 requests in 22.05s, 3.58MB read
  Socket errors: connect 0, read 0, write 0, timeout 14000
Requests/sec:    635.06
Transfer/sec:    166.21KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s    60.35ms   1.36s    82.26%
    Req/Sec   113.59     95.31   820.00     73.96%
  35659 requests in 22.10s, 9.11MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1613.63
Transfer/sec:    422.32KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   218.40    227.18   818.00     83.95%
  4000 requests in 22.05s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.39
Transfer/sec:     47.47KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   185.20    165.91   610.00     57.30%
  2000 requests in 22.04s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:     90.74
Transfer/sec:     23.75KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   443.45ms   2.00s    77.98%
    Req/Sec     7.19     12.17    80.00     87.41%
  611 requests in 22.04s, 14.83MB read
  Socket errors: connect 0, read 0, write 0, timeout 284
  Non-2xx or 3xx responses: 3
Requests/sec:     27.72
Transfer/sec:    689.01KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.04s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    12.05     16.15    80.00     82.50%
  79 requests in 22.04s, 1.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 79
Requests/sec:      3.58
Transfer/sec:     89.53KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.03s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.95s    32.08ms   1.97s   100.00%
    Req/Sec     6.68      7.03    40.00     88.68%
  533 requests in 22.04s, 13.00MB read
  Socket errors: connect 0, read 0, write 0, timeout 531
Requests/sec:     24.18
Transfer/sec:    603.84KB
```

## ASGI Hypercorn Asyncio
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   128.11ms   1.85s    90.17%
    Req/Sec   101.76     77.18   848.00     76.44%
  38561 requests in 22.10s, 10.02MB read
Requests/sec:   1744.97
Transfer/sec:    464.18KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s    85.79ms   1.95s    92.69%
    Req/Sec    98.02     71.59   616.00     71.04%
  36594 requests in 22.04s, 9.51MB read
  Socket errors: connect 0, read 0, write 0, timeout 588
Requests/sec:   1660.22
Transfer/sec:    441.77KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    99.01     98.92   606.00     77.62%
  12920 requests in 22.04s, 3.36MB read
  Socket errors: connect 0, read 0, write 0, timeout 12920
Requests/sec:    586.14
Transfer/sec:    156.01KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s    67.39ms   1.51s    87.32%
    Req/Sec   101.36     73.56   790.00     76.17%
  32912 requests in 22.10s, 8.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 240
Requests/sec:   1489.31
Transfer/sec:    396.29KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   142.51    150.21   696.00     84.78%
  4000 requests in 22.04s, 1.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.48
Transfer/sec:     48.21KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    90.30    116.41   520.00     87.14%
  1250 requests in 22.04s, 332.03KB read
  Socket errors: connect 0, read 0, write 0, timeout 1250
Requests/sec:     56.71
Transfer/sec:     15.06KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   949.90ms  161.89ms   1.39s    83.72%
    Req/Sec     3.21      6.07    60.00     85.71%
  363 requests in 22.04s, 8.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 320
  Non-2xx or 3xx responses: 15
Requests/sec:     16.47
Transfer/sec:    394.60KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.04s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.05s, 0.00B read
  Socket errors: connect 0, read 41, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.52s   339.04ms   1.98s    73.42%
    Req/Sec     6.56     11.13   101.00     88.25%
  481 requests in 22.03s, 11.73MB read
  Socket errors: connect 0, read 82, write 0, timeout 402
Requests/sec:     21.83
Transfer/sec:    545.30KB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.71s    63.96ms   1.77s   100.00%
    Req/Sec     2.92      4.51    30.00     85.29%
  414 requests in 22.10s, 10.10MB read
  Socket errors: connect 0, read 0, write 0, timeout 410
Requests/sec:     18.73
Transfer/sec:    467.93KB
```

## ASGI Hypercorn Uvloop
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    98.80ms   1.85s    95.83%
    Req/Sec   104.41     82.31   840.00     76.04%
  39633 requests in 22.10s, 10.28MB read
  Socket errors: connect 0, read 0, write 0, timeout 40
Requests/sec:   1793.58
Transfer/sec:    476.42KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    92.14ms   2.00s    93.80%
    Req/Sec   107.77     91.37   770.00     79.89%
  38311 requests in 22.09s, 9.94MB read
  Socket errors: connect 0, read 0, write 0, timeout 127
Requests/sec:   1734.09
Transfer/sec:    460.62KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   101.56    134.60   808.00     84.09%
  12743 requests in 22.09s, 3.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 12743
Requests/sec:    576.77
Transfer/sec:    153.20KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s    36.26ms   1.42s    92.23%
    Req/Sec    93.06     89.65   666.00     84.02%
  25823 requests in 22.03s, 6.70MB read
  Socket errors: connect 0, read 0, write 0, timeout 1071
Requests/sec:   1172.25
Transfer/sec:    311.38KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    73.92    138.55   848.00     88.24%
  3592 requests in 22.10s, 0.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 3592
Requests/sec:    162.56
Transfer/sec:     43.18KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    39.95     63.20   370.00     87.80%
  714 requests in 22.04s, 189.66KB read
  Socket errors: connect 0, read 51, write 0, timeout 714
Requests/sec:     32.40
Transfer/sec:      8.61KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.38s   206.38ms   1.75s    64.00%
    Req/Sec     3.50      5.76    40.00     82.03%
  357 requests in 22.04s, 8.16MB read
  Socket errors: connect 0, read 0, write 0, timeout 307
  Non-2xx or 3xx responses: 23
Requests/sec:     16.20
Transfer/sec:    378.99KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.04s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.04s, 0.00B read
  Socket errors: connect 0, read 45, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.38s   311.10ms   1.95s    61.38%
    Req/Sec    11.69     11.29    60.00     74.60%
  410 requests in 22.04s, 10.00MB read
  Socket errors: connect 0, read 14, write 0, timeout 265
Requests/sec:     18.61
Transfer/sec:    464.71KB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.49s   309.86ms   1.95s    50.00%
    Req/Sec     5.36      6.10    50.00     93.33%
  821 requests in 22.03s, 20.03MB read
  Socket errors: connect 0, read 0, write 0, timeout 775
Requests/sec:     37.26
Transfer/sec:      0.91MB
```
