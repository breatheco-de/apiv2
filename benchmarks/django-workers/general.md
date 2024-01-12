# Django Workers
## WSGI Gunicorn Gevent

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   198.09ms  391.23ms   2.00s    85.99%
    Req/Sec     1.64k     0.86k    6.95k    68.54%
  312239 requests in 10.10s, 91.42MB read
  Socket errors: connect 0, read 20, write 0, timeout 2978
Requests/sec:  30913.89
Transfer/sec:      9.05MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    93.70ms  246.97ms   2.00s    88.40%
    Req/Sec     1.65k   738.39     4.21k    66.29%
  115974 requests in 10.09s, 138.03MB read
  Socket errors: connect 0, read 0, write 0, timeout 235
Requests/sec:  11498.22
Transfer/sec:     13.69MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    65.67ms  209.31ms   2.00s    90.61%
    Req/Sec     1.46k   727.22     4.90k    76.47%
  71819 requests in 10.10s, 212.39MB read
  Socket errors: connect 0, read 0, write 0, timeout 199
Requests/sec:   7113.50
Transfer/sec:     21.04MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    63.21ms   1.34s    95.60%
    Req/Sec   117.19    160.55     0.96k    95.07%
  16874 requests in 10.10s, 4.72MB read
Requests/sec:   1670.83
Transfer/sec:    478.08KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   285.53    407.60     1.00k    69.77%
  6000 requests in 10.10s, 1.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    594.02
Transfer/sec:    169.97KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   134.39    218.29   570.00     72.22%
  859 requests in 10.10s, 247.41KB read
  Socket errors: connect 0, read 0, write 0, timeout 859
Requests/sec:     85.06
Transfer/sec:     24.50KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    54.89ms   96.67ms   1.98s    99.19%
    Req/Sec    53.62     31.64   150.00     52.38%
  4186 requests in 10.10s, 26.85MB read
  Socket errors: connect 0, read 0, write 0, timeout 96
Requests/sec:    414.45
Transfer/sec:      2.66MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.85s    48.07ms   1.92s    66.67%
    Req/Sec     5.01      5.97    30.00     92.65%
  256 requests in 10.09s, 6.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 250
Requests/sec:     25.37
Transfer/sec:    634.25KB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.85s   111.30ms   1.96s    66.67%
    Req/Sec     2.10      4.10    20.00     89.74%
  43 requests in 10.10s, 0.98MB read
  Socket errors: connect 0, read 0, write 0, timeout 34
  Non-2xx or 3xx responses: 3
Requests/sec:      4.26
Transfer/sec:     99.15KB
```

## ASGI Gunicorn Uvicorn

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   478.72ms  170.86ms   1.43s    78.94%
    Req/Sec   219.25     74.76   620.00     74.48%
  41009 requests in 10.10s, 11.03MB read
Requests/sec:   4061.19
Transfer/sec:      1.09MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   561.49ms  183.06ms   1.73s    75.50%
    Req/Sec   181.93     63.32   530.00     71.37%
  34992 requests in 10.10s, 9.41MB read
Requests/sec:   3464.25
Transfer/sec:      0.93MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.00s   208.32ms   2.00s    82.81%
    Req/Sec   100.18     46.47   400.00     70.90%
  18637 requests in 10.10s, 21.74MB read
  Socket errors: connect 0, read 0, write 0, timeout 278
Requests/sec:   1845.01
Transfer/sec:      2.15MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   938.97ms  201.67ms   2.00s    82.89%
    Req/Sec   108.17     55.21   444.00     73.21%
  20170 requests in 10.10s, 23.53MB read
  Socket errors: connect 0, read 0, write 0, timeout 185
Requests/sec:   1997.32
Transfer/sec:      2.33MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   284.93ms   2.00s    75.10%
    Req/Sec    85.59     39.63   303.00     71.11%
  15957 requests in 10.03s, 46.81MB read
  Socket errors: connect 0, read 0, write 0, timeout 768
Requests/sec:   1590.24
Transfer/sec:      4.66MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s   193.61ms   2.00s    82.17%
    Req/Sec    97.43     55.80   383.00     70.68%
  17668 requests in 10.10s, 51.83MB read
  Socket errors: connect 0, read 0, write 0, timeout 403
Requests/sec:   1749.29
Transfer/sec:      5.13MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   108.32ms   1.54s    89.08%
    Req/Sec   145.03    167.76     0.88k    86.35%
  17876 requests in 10.10s, 4.57MB read
Requests/sec:   1769.90
Transfer/sec:    463.22KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.14s   262.68ms   2.00s    88.49%
    Req/Sec   126.99    111.28   782.00     73.57%
  16513 requests in 10.09s, 4.22MB read
  Socket errors: connect 0, read 0, write 0, timeout 113
Requests/sec:   1635.91
Transfer/sec:    428.15KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   187.58    173.52   696.00     59.66%
  6000 requests in 10.10s, 1.53MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    594.15
Transfer/sec:    155.50KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s    44.47ms   1.32s    89.77%
    Req/Sec   139.41    123.14   696.00     71.89%
  13598 requests in 10.02s, 3.48MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1357.19
Transfer/sec:    355.20KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     3.00      1.29     5.00     71.43%
  263 requests in 10.10s, 68.83KB read
  Socket errors: connect 0, read 0, write 0, timeout 263
Requests/sec:     26.04
Transfer/sec:      6.81KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 28, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   529.47ms   1.99s    60.76%
    Req/Sec    24.81     22.00   150.00     81.02%
  2987 requests in 10.10s, 19.09MB read
  Socket errors: connect 0, read 0, write 0, timeout 2829
Requests/sec:    295.72
Transfer/sec:      1.89MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    42.01     34.01   161.00     74.18%
  1596 requests in 10.10s, 10.20MB read
  Socket errors: connect 0, read 0, write 0, timeout 1596
Requests/sec:    158.04
Transfer/sec:      1.01MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   766.01ms  205.13ms   1.51s    79.44%
    Req/Sec    11.80     19.70   111.00     88.24%
  238 requests in 10.09s, 5.80MB read
  Socket errors: connect 0, read 0, write 0, timeout 131
Requests/sec:     23.59
Transfer/sec:    589.16KB
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
    Latency     1.36s   200.35ms   1.87s    84.00%
    Req/Sec     5.78     10.77    70.00     93.48%
  194 requests in 10.09s, 3.17MB read
  Socket errors: connect 0, read 194, write 0, timeout 169
  Non-2xx or 3xx responses: 65
Requests/sec:     19.23
Transfer/sec:    322.16KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   441.77ms   1.99s    67.14%
    Req/Sec     9.04      8.96    70.00     83.01%
  530 requests in 10.10s, 12.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 460
Requests/sec:     52.47
Transfer/sec:      1.28MB
```

## ASGI Hypercorn Asyncio

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   504.67ms  396.40ms   2.00s    83.71%
    Req/Sec   204.84    126.51     1.10k    73.10%
  37875 requests in 10.09s, 10.36MB read
  Socket errors: connect 0, read 0, write 0, timeout 574
Requests/sec:   3753.90
Transfer/sec:      1.03MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   579.33ms  313.64ms   1.92s    77.84%
    Req/Sec   173.00    110.51   808.00     69.43%
  33038 requests in 10.10s, 9.04MB read
Requests/sec:   3270.73
Transfer/sec:      0.90MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   785.29ms  470.09ms   2.00s    66.39%
    Req/Sec    91.16     65.99   484.00     70.41%
  17073 requests in 10.10s, 20.00MB read
  Socket errors: connect 0, read 0, write 0, timeout 1413
Requests/sec:   1691.03
Transfer/sec:      1.98MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.00s   435.21ms   2.00s    69.79%
    Req/Sec    84.58     57.83   424.00     70.38%
  15797 requests in 10.09s, 18.50MB read
  Socket errors: connect 0, read 0, write 0, timeout 1260
Requests/sec:   1565.80
Transfer/sec:      1.83MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   966.61ms  537.89ms   2.00s    60.57%
    Req/Sec    63.69     38.90   240.00     70.34%
  11993 requests in 10.08s, 35.24MB read
  Socket errors: connect 0, read 0, write 0, timeout 2540
Requests/sec:   1189.28
Transfer/sec:      3.49MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s   451.86ms   2.00s    65.05%
    Req/Sec    78.71     64.62   434.00     75.32%
  13949 requests in 10.09s, 40.99MB read
  Socket errors: connect 0, read 0, write 0, timeout 1900
Requests/sec:   1382.19
Transfer/sec:      4.06MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   142.09ms   1.70s    86.70%
    Req/Sec    98.16     82.16   550.00     76.01%
  15120 requests in 10.10s, 3.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 87
Requests/sec:   1497.21
Transfer/sec:    398.84KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.18s   207.25ms   1.92s    87.57%
    Req/Sec   104.86    101.98   770.00     84.63%
  13599 requests in 10.10s, 3.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 384
Requests/sec:   1346.70
Transfer/sec:    359.75KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   125.66    137.04   666.00     82.45%
  5501 requests in 10.10s, 1.43MB read
  Socket errors: connect 0, read 0, write 0, timeout 5501
Requests/sec:    544.69
Transfer/sec:    144.68KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s    80.79ms   1.44s    85.53%
    Req/Sec    93.66    106.17   770.00     86.29%
  9822 requests in 10.02s, 2.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 1607
Requests/sec:    980.24
Transfer/sec:    261.00KB
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
  Socket errors: connect 0, read 106, write 0, timeout 0
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
  0 requests in 10.02s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.34s   462.40ms   1.99s    59.61%
    Req/Sec    23.87     24.92   232.00     86.28%
  3177 requests in 10.11s, 20.32MB read
  Socket errors: connect 0, read 0, write 0, timeout 2662
Requests/sec:    314.35
Transfer/sec:      2.01MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   659.10ms  763.49ms   2.00s    69.23%
    Req/Sec    39.74     88.39   840.00     89.57%
  1438 requests in 10.09s, 9.20MB read
  Socket errors: connect 0, read 0, write 0, timeout 1256
Requests/sec:    142.45
Transfer/sec:      0.91MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s   313.21ms   1.99s    76.92%
    Req/Sec     5.56      7.52    40.00     88.60%
  154 requests in 10.10s, 3.76MB read
  Socket errors: connect 0, read 0, write 0, timeout 115
Requests/sec:     15.25
Transfer/sec:    380.81KB
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
  0 requests in 10.02s, 0.00B read
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
    Req/Sec     7.93      6.76    30.00     66.92%
  194 requests in 10.02s, 4.73MB read
  Socket errors: connect 0, read 0, write 0, timeout 194
Requests/sec:     19.37
Transfer/sec:    483.72KB
```

## ASGI Hypercorn Uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   344.54ms  145.74ms   2.00s    84.87%
    Req/Sec   261.97    125.79   828.00     74.26%
  49781 requests in 10.10s, 13.58MB read
  Socket errors: connect 0, read 0, write 0, timeout 197
Requests/sec:   4929.08
Transfer/sec:      1.34MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   275.21ms  130.95ms 670.16ms   64.22%
    Req/Sec   229.30    146.20     1.12k    71.46%
  45787 requests in 10.10s, 12.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 455
Requests/sec:   4533.80
Transfer/sec:      1.24MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   774.26ms  365.05ms   1.98s    68.70%
    Req/Sec   100.68     65.40   636.00     75.57%
  19870 requests in 10.09s, 23.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 360
Requests/sec:   1969.74
Transfer/sec:      2.30MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   466.33ms  265.00ms   1.79s    67.32%
    Req/Sec   118.18    120.16     1.26k    93.09%
  21659 requests in 10.08s, 25.34MB read
  Socket errors: connect 0, read 0, write 0, timeout 342
Requests/sec:   2148.56
Transfer/sec:      2.51MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   691.26ms  404.75ms   2.00s    67.89%
    Req/Sec    88.76     86.80   777.00     92.16%
  15939 requests in 10.10s, 46.82MB read
  Socket errors: connect 0, read 0, write 0, timeout 1081
Requests/sec:   1577.94
Transfer/sec:      4.63MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   619.38ms  298.74ms   2.00s    70.44%
    Req/Sec    96.32     88.82   838.00     89.33%
  18105 requests in 10.10s, 53.18MB read
  Socket errors: connect 0, read 0, write 0, timeout 372
Requests/sec:   1792.08
Transfer/sec:      5.26MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    45.92ms   1.28s    92.14%
    Req/Sec   126.58    127.04     0.99k    84.97%
  12285 requests in 10.10s, 3.19MB read
  Socket errors: connect 0, read 0, write 0, timeout 561
Requests/sec:   1216.86
Transfer/sec:    323.23KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    84.32ms   1.95s    95.35%
    Req/Sec    73.03     91.21   707.00     88.25%
  8598 requests in 10.10s, 2.23MB read
  Socket errors: connect 0, read 0, write 0, timeout 494
Requests/sec:    851.47
Transfer/sec:    226.17KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    90.42    150.41   840.00     87.01%
  4211 requests in 10.10s, 1.09MB read
  Socket errors: connect 0, read 0, write 0, timeout 4211
Requests/sec:    416.96
Transfer/sec:    110.76KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    53.09ms   1.46s    93.44%
    Req/Sec   110.52    141.16     0.89k    85.95%
  7789 requests in 10.10s, 2.02MB read
  Socket errors: connect 0, read 49, write 0, timeout 779
Requests/sec:    771.33
Transfer/sec:    204.88KB
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
  Socket errors: connect 0, read 241, write 0, timeout 0
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
    Latency     1.30s   536.91ms   2.00s    60.04%
    Req/Sec    26.13     24.69   230.00     84.63%
  3272 requests in 10.09s, 20.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 2779
Requests/sec:    324.34
Transfer/sec:      2.07MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.68s   258.58ms   2.00s    62.18%
    Req/Sec    26.12     29.81   198.00     86.35%
  1949 requests in 10.09s, 12.46MB read
  Socket errors: connect 0, read 0, write 0, timeout 1756
Requests/sec:    193.18
Transfer/sec:      1.24MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   354.80ms   1.99s    69.53%
    Req/Sec     8.32     13.97   100.00     92.64%
  255 requests in 10.10s, 6.22MB read
  Socket errors: connect 0, read 65, write 0, timeout 127
Requests/sec:     25.25
Transfer/sec:    630.70KB
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
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    14.24     18.39   131.00     92.31%
  166 requests in 10.09s, 4.05MB read
  Socket errors: connect 0, read 0, write 0, timeout 166
Requests/sec:     16.45
Transfer/sec:    410.87KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.28s   453.53ms   1.99s    50.72%
    Req/Sec    10.22     10.41    60.00     89.77%
  406 requests in 10.02s, 9.90MB read
  Socket errors: connect 0, read 74, write 0, timeout 337
Requests/sec:     40.51
Transfer/sec:      0.99MB
```
