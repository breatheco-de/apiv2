# Django Workers
## ASGI Gunicorn Uvicorn Asyncio

### JSON performance
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   342.85ms  147.58ms   1.45s    68.73%
    Req/Sec   298.32     83.16   700.00     69.47%
  127833 requests in 22.05s, 34.38MB read
  Socket errors: connect 0, read 0, write 0, timeout 173
Requests/sec:   5798.47
Transfer/sec:      1.56MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   331.63ms   70.00ms   1.04s    75.69%
    Req/Sec   303.52     68.00   831.00     72.20%
  132100 requests in 22.05s, 35.53MB read
Requests/sec:   5991.89
Transfer/sec:      1.61MB
```

### Queries returned as JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   904.13ms  200.76ms   1.61s    72.72%
    Req/Sec   110.00     49.77   720.00     72.99%
  47613 requests in 22.10s, 55.53MB read
Requests/sec:   2154.43
Transfer/sec:      2.51MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   975.94ms  183.44ms   2.00s    78.82%
    Req/Sec   102.33     45.29   480.00     72.68%
  44131 requests in 22.06s, 51.47MB read
  Socket errors: connect 0, read 0, write 0, timeout 62
Requests/sec:   2000.24
Transfer/sec:      2.33MB
```

### Queries returned as HTML
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.08s   316.66ms   2.00s    72.46%
    Req/Sec    89.98     34.90   340.00     70.71%
  38421 requests in 22.07s, 112.71MB read
  Socket errors: connect 0, read 0, write 0, timeout 1305
Requests/sec:   1741.19
Transfer/sec:      5.11MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s   161.55ms   2.00s    79.32%
    Req/Sec    96.63     41.52   475.00     70.39%
  40954 requests in 22.05s, 120.14MB read
  Socket errors: connect 0, read 0, write 0, timeout 317
Requests/sec:   1857.12
Transfer/sec:      5.45MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    73.81ms   1.50s    94.15%
    Req/Sec   131.71    132.44     0.94k    87.31%
  41519 requests in 22.10s, 10.61MB read
Requests/sec:   1878.86
Transfer/sec:    491.73KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   153.03ms   2.00s    95.24%
    Req/Sec   114.93     92.37   633.00     69.78%
  39346 requests in 22.10s, 10.06MB read
  Socket errors: connect 0, read 0, write 0, timeout 896
Requests/sec:   1780.40
Transfer/sec:    465.96KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   128.44    133.25   770.00     87.90%
  13902 requests in 22.05s, 3.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 13902
Requests/sec:    630.60
Transfer/sec:    165.04KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.08s    82.07ms   1.40s    83.07%
    Req/Sec   107.95     82.89   760.00     72.10%
  34790 requests in 22.09s, 8.89MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1575.03
Transfer/sec:    412.22KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   200.01    182.41   680.00     54.60%
  4000 requests in 22.04s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.45
Transfer/sec:     47.49KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   213.77    211.60   770.00     55.13%
  2000 requests in 22.04s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:     90.73
Transfer/sec:     23.75KB
```

### Brotli
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.50s   382.68ms   2.00s    54.10%
    Req/Sec    25.03     22.97   171.00     80.25%
  7367 requests in 22.10s, 47.09MB read
  Socket errors: connect 0, read 0, write 0, timeout 7306
Requests/sec:    333.35
Transfer/sec:      2.13MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.96s     0.00us   1.96s   100.00%
    Req/Sec    49.88     41.83   292.00     74.76%
  5517 requests in 22.10s, 35.26MB read
  Socket errors: connect 0, read 0, write 0, timeout 5516
Requests/sec:    249.67
Transfer/sec:      1.60MB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   990.69ms  216.73ms   1.70s    87.32%
    Req/Sec     5.67      7.27    40.00     91.10%
  394 requests in 22.10s, 9.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 323
  Non-2xx or 3xx responses: 15
Requests/sec:     17.83
Transfer/sec:    428.56KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.05s, 0.00B read
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
    Latency     1.92s    18.94ms   1.93s   100.00%
    Req/Sec     7.84      8.39    50.00     88.37%
  829 requests in 22.04s, 20.22MB read
  Socket errors: connect 0, read 5, write 0, timeout 827
Requests/sec:     37.61
Transfer/sec:      0.92MB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.37s   345.32ms   1.97s    60.87%
    Req/Sec     6.22      6.43    60.00     92.00%
  1093 requests in 22.05s, 26.66MB read
  Socket errors: connect 0, read 0, write 0, timeout 1024
Requests/sec:     49.57
Transfer/sec:      1.21MB
```

## ASGI Gunicorn Uvicorn Uvloop

### JSON performance
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   347.71ms   97.13ms   1.31s    84.50%
    Req/Sec   295.63     71.55     0.89k    73.67%
  126652 requests in 22.08s, 34.06MB read
Requests/sec:   5736.53
Transfer/sec:      1.54MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   402.11ms  134.86ms   1.09s    73.68%
    Req/Sec   248.99     85.15   676.00     67.72%
  108383 requests in 22.06s, 29.15MB read
Requests/sec:   4913.73
Transfer/sec:      1.32MB
```

### Queries returned as JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   964.61ms  161.94ms   2.00s    80.71%
    Req/Sec   104.20     43.85   590.00     68.55%
  44415 requests in 22.06s, 51.80MB read
  Socket errors: connect 0, read 0, write 0, timeout 166
Requests/sec:   2013.56
Transfer/sec:      2.35MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   937.05ms  166.62ms   2.00s    80.11%
    Req/Sec   107.87     45.30   494.00     71.10%
  46045 requests in 22.07s, 53.70MB read
  Socket errors: connect 0, read 0, write 0, timeout 64
Requests/sec:   2086.25
Transfer/sec:      2.43MB
```

### Queries returned as HTML
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   314.91ms   2.00s    69.55%
    Req/Sec    85.57     34.58   346.00     68.35%
  36386 requests in 22.07s, 106.74MB read
  Socket errors: connect 0, read 0, write 0, timeout 1475
Requests/sec:   1648.98
Transfer/sec:      4.84MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s   170.54ms   2.00s    78.57%
    Req/Sec    96.34     44.77   434.00     70.78%
  40872 requests in 22.06s, 119.90MB read
  Socket errors: connect 0, read 0, write 0, timeout 276
Requests/sec:   1853.04
Transfer/sec:      5.44MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    74.54ms   1.51s    93.84%
    Req/Sec   133.33    130.61     0.86k    85.41%
  41471 requests in 22.09s, 10.60MB read
Requests/sec:   1877.11
Transfer/sec:    491.27KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   131.05ms   2.00s    94.02%
    Req/Sec   106.14     77.68   650.00     75.26%
  39175 requests in 22.03s, 10.01MB read
  Socket errors: connect 0, read 0, write 0, timeout 1267
Requests/sec:   1778.23
Transfer/sec:    465.40KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   130.81    115.04   750.00     70.51%
  13861 requests in 22.05s, 3.54MB read
  Socket errors: connect 0, read 0, write 0, timeout 13861
Requests/sec:    628.70
Transfer/sec:    164.54KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s    82.64ms   1.45s    85.70%
    Req/Sec   110.00     88.51   828.00     73.26%
  35041 requests in 22.03s, 8.96MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1590.71
Transfer/sec:    416.32KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   196.73    182.16   686.00     56.40%
  4000 requests in 22.05s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.41
Transfer/sec:     47.48KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   179.90    166.15   560.00     54.95%
  2000 requests in 22.05s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:     90.71
Transfer/sec:     23.74KB
```

### Brotli
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.44s   396.69ms   1.99s    68.52%
    Req/Sec    21.65     17.31   130.00     74.97%
  7338 requests in 22.09s, 46.90MB read
  Socket errors: connect 0, read 0, write 0, timeout 7230
Requests/sec:    332.12
Transfer/sec:      2.12MB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.92s    79.33ms   1.99s    82.35%
    Req/Sec    43.11     37.58   272.00     76.64%
  5457 requests in 22.10s, 34.88MB read
  Socket errors: connect 0, read 0, write 0, timeout 5440
Requests/sec:    246.94
Transfer/sec:      1.58MB
```

### Requests
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   823.18ms  247.84ms   1.46s    71.54%
    Req/Sec     5.12      8.75    50.00     89.12%
  389 requests in 22.08s, 9.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 266
  Non-2xx or 3xx responses: 3
Requests/sec:     17.62
Transfer/sec:    436.59KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 22.05s, 0.00B read
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
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.75s   155.15ms   1.98s    66.67%
    Req/Sec     9.53     11.00   120.00     92.61%
  865 requests in 22.05s, 21.10MB read
  Socket errors: connect 0, read 0, write 0, timeout 802
Requests/sec:     39.24
Transfer/sec:      0.96MB
```

### AIOHTTP
#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.34s   357.14ms   1.97s    63.83%
    Req/Sec     6.55      6.55    60.00     91.07%
  1090 requests in 22.04s, 26.58MB read
  Socket errors: connect 0, read 0, write 0, timeout 1043
Requests/sec:     49.45
Transfer/sec:      1.21MB
```
