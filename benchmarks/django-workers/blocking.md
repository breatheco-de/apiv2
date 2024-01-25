# Django Workers
## WSGI Gunicorn Gevent
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    85.17ms   1.68s    96.79%
    Req/Sec   131.01    126.38   700.00     87.41%
  41146 requests in 22.10s, 11.50MB read
  Socket errors: connect 0, read 0, write 0, timeout 482
Requests/sec:   1861.80
Transfer/sec:    532.72KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   261.24    355.69     1.00k    74.89%
  14000 requests in 22.04s, 3.91MB read
  Socket errors: connect 0, read 0, write 0, timeout 14000
Requests/sec:    635.14
Transfer/sec:    181.73KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   203.32    273.28     0.98k    83.56%
  4000 requests in 22.05s, 1.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.38
Transfer/sec:     51.90KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.45s   404.48ms   1.94s    59.09%
    Req/Sec     6.03      7.15    50.00     90.21%
  849 requests in 22.05s, 20.70MB read
  Socket errors: connect 0, read 0, write 0, timeout 805
  Non-2xx or 3xx responses: 1
Requests/sec:     38.50
Transfer/sec:      0.94MB
```

### HTTPX
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.09      0.30     1.00     90.91%
  11 requests in 22.10s, 250.28KB read
  Socket errors: connect 0, read 0, write 0, timeout 11
  Non-2xx or 3xx responses: 1
Requests/sec:      0.50
Transfer/sec:     11.32KB
```

## ASGI Gunicorn Uvicorn
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   163.35ms   1.90s    94.71%
    Req/Sec   117.88     99.66     1.00k    77.65%
  40223 requests in 22.10s, 10.28MB read
Requests/sec:   1819.99
Transfer/sec:    476.33KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s   102.80ms   2.00s    98.09%
    Req/Sec   128.29    111.31   666.00     70.64%
  39763 requests in 22.03s, 10.16MB read
  Socket errors: connect 0, read 0, write 0, timeout 1565
Requests/sec:   1805.06
Transfer/sec:    472.42KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   152.95    136.41     0.93k    66.54%
  13930 requests in 22.04s, 3.56MB read
  Socket errors: connect 0, read 0, write 0, timeout 13930
Requests/sec:    631.95
Transfer/sec:    165.39KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s    69.55ms   1.36s    84.14%
    Req/Sec   109.28     87.84   727.00     70.80%
  35067 requests in 22.02s, 8.96MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1592.22
Transfer/sec:    416.71KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   199.23    202.76   780.00     82.50%
  4000 requests in 22.05s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.37
Transfer/sec:     47.47KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   185.91    200.26   727.00     82.02%
  2000 requests in 22.05s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:     90.72
Transfer/sec:     23.74KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   999.72ms  334.90ms   2.00s    78.67%
    Req/Sec     8.18     12.04    70.00     90.59%
  553 requests in 22.05s, 13.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 253
Requests/sec:     25.08
Transfer/sec:    626.28KB
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
  0 requests in 22.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.73s    50.59ms   1.85s    80.95%
    Req/Sec     5.25      5.27    40.00     95.82%
  944 requests in 22.05s, 23.00MB read
  Socket errors: connect 0, read 0, write 0, timeout 923
  Non-2xx or 3xx responses: 1
Requests/sec:     42.81
Transfer/sec:      1.04MB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     5.11      5.00    30.00     82.05%
  773 requests in 22.04s, 18.85MB read
  Socket errors: connect 0, read 0, write 0, timeout 773
Requests/sec:     35.07
Transfer/sec:      0.86MB
```

## ASGI Hypercorn Asyncio
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s   112.72ms   1.75s    93.29%
    Req/Sec   105.13     89.70   630.00     76.67%
  38607 requests in 22.10s, 10.04MB read
Requests/sec:   1747.01
Transfer/sec:    465.37KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s    97.50ms   2.00s    93.54%
    Req/Sec   101.16     78.65   600.00     67.70%
  37044 requests in 22.10s, 9.62MB read
  Socket errors: connect 0, read 0, write 0, timeout 404
Requests/sec:   1676.20
Transfer/sec:    445.73KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    95.32     87.33   480.00     73.85%
  12905 requests in 22.04s, 3.36MB read
  Socket errors: connect 0, read 0, write 0, timeout 12905
Requests/sec:    585.55
Transfer/sec:    156.34KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s    92.30ms   1.91s    88.48%
    Req/Sec    95.38     79.06   680.00     74.35%
  32625 requests in 22.10s, 8.48MB read
  Socket errors: connect 0, read 0, write 0, timeout 1238
Requests/sec:   1476.54
Transfer/sec:    393.11KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   136.74    167.03   760.00     87.18%
  4000 requests in 22.05s, 1.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.43
Transfer/sec:     48.19KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    44.25     90.30   640.00     93.33%
  837 requests in 22.04s, 222.33KB read
  Socket errors: connect 0, read 0, write 0, timeout 837
Requests/sec:     37.97
Transfer/sec:     10.09KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   378.79ms   1.95s    67.21%
    Req/Sec     3.87      6.31    40.00     93.92%
  487 requests in 22.10s, 11.66MB read
  Socket errors: connect 0, read 0, write 0, timeout 365
  Non-2xx or 3xx responses: 9
Requests/sec:     22.04
Transfer/sec:    540.33KB
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
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.89s   533.16us   1.89s   100.00%
    Req/Sec     7.24      7.94    50.00     88.17%
  391 requests in 22.04s, 9.54MB read
  Socket errors: connect 0, read 1, write 0, timeout 389
Requests/sec:     17.74
Transfer/sec:    443.12KB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.77s    99.19ms   1.91s    71.43%
    Req/Sec     3.61      5.59    40.00     83.18%
  516 requests in 22.05s, 12.59MB read
  Socket errors: connect 0, read 0, write 0, timeout 509
Requests/sec:     23.40
Transfer/sec:    584.60KB
```

## ASGI Hypercorn Uvloop
### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    99.48ms   1.87s    96.14%
    Req/Sec   106.63     94.64   770.00     78.18%
  39091 requests in 22.09s, 10.14MB read
  Socket errors: connect 0, read 0, write 0, timeout 58
Requests/sec:   1769.52
Transfer/sec:    470.03KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    92.80ms   1.98s    97.24%
    Req/Sec   106.13     92.61   630.00     74.05%
  37838 requests in 22.10s, 9.82MB read
  Socket errors: connect 0, read 0, write 0, timeout 421
Requests/sec:   1712.17
Transfer/sec:    454.80KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    99.67    127.73     0.88k    85.67%
  12784 requests in 22.09s, 3.32MB read
  Socket errors: connect 0, read 0, write 0, timeout 12784
Requests/sec:    578.60
Transfer/sec:    153.69KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s    71.61ms   1.85s    96.02%
    Req/Sec    98.48     88.85   780.00     81.97%
  30836 requests in 22.10s, 8.00MB read
  Socket errors: connect 0, read 0, write 0, timeout 948
Requests/sec:   1395.52
Transfer/sec:    370.69KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    65.02    130.50   740.00     93.52%
  3362 requests in 22.05s, 0.87MB read
  Socket errors: connect 0, read 0, write 0, timeout 3362
Requests/sec:    152.51
Transfer/sec:     40.51KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    72.63    132.44   650.00     87.80%
  642 requests in 22.04s, 170.53KB read
  Socket errors: connect 0, read 86, write 0, timeout 642
Requests/sec:     29.12
Transfer/sec:      7.74KB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   290.27ms   1.94s    72.37%
    Req/Sec     3.26      6.60    70.00     84.27%
  353 requests in 22.05s, 7.91MB read
  Socket errors: connect 0, read 0, write 0, timeout 277
  Non-2xx or 3xx responses: 29
Requests/sec:     16.01
Transfer/sec:    367.38KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.04s, 0.00B read
  Socket errors: connect 0, read 48, write 0, timeout 0
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
  Socket errors: connect 0, read 2, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   341.75ms   1.99s    68.18%
    Req/Sec    10.79     11.92    70.00     87.55%
  384 requests in 22.04s, 9.37MB read
  Socket errors: connect 0, read 93, write 0, timeout 76
Requests/sec:     17.42
Transfer/sec:    435.16KB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   339.27ms   1.99s    60.87%
    Req/Sec     6.20      6.83    60.00     91.68%
  1001 requests in 22.10s, 24.42MB read
  Socket errors: connect 0, read 59, write 0, timeout 932
Requests/sec:     45.29
Transfer/sec:      1.10MB
```
