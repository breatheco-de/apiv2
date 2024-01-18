# Django Workers
## ASGI Gunicorn Uvicorn

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   370.32ms  176.96ms   1.50s    69.70%
    Req/Sec   281.84     98.35   770.00     71.93%
  53284 requests in 10.10s, 14.33MB read
  Socket errors: connect 0, read 0, write 0, timeout 126
Requests/sec:   5278.10
Transfer/sec:      1.42MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   371.51ms   87.18ms   1.01s    73.69%
    Req/Sec   269.37     85.87     0.88k    73.65%
  53065 requests in 10.10s, 14.27MB read
Requests/sec:   5255.49
Transfer/sec:      1.41MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   597.39ms  110.68ms   1.40s    82.06%
    Req/Sec   165.50     66.06   610.00     73.37%
  32380 requests in 10.09s, 37.77MB read
Requests/sec:   3209.35
Transfer/sec:      3.74MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   601.01ms  115.24ms   1.53s    88.00%
    Req/Sec   168.29     72.11   680.00     75.84%
  32514 requests in 10.10s, 37.92MB read
Requests/sec:   3219.04
Transfer/sec:      3.75MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   731.18ms  205.12ms   2.00s    81.70%
    Req/Sec   137.38     52.28   454.00     70.99%
  26343 requests in 10.03s, 77.28MB read
  Socket errors: connect 0, read 0, write 0, timeout 10
Requests/sec:   2625.96
Transfer/sec:      7.70MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   795.66ms  190.47ms   1.76s    75.29%
    Req/Sec   125.52     58.92   590.00     76.35%
  24020 requests in 10.10s, 70.46MB read
Requests/sec:   2378.17
Transfer/sec:      6.98MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   119.12ms   1.59s    89.24%
    Req/Sec   203.11    223.87     0.99k    80.85%
  18000 requests in 10.10s, 4.60MB read
Requests/sec:   1782.12
Transfer/sec:    466.41KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   264.13ms   2.00s    88.63%
    Req/Sec   162.03    139.65     0.89k    61.58%
  16897 requests in 10.04s, 4.32MB read
  Socket errors: connect 0, read 0, write 0, timeout 88
Requests/sec:   1682.35
Transfer/sec:    440.30KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   216.16    201.58     0.94k    54.39%
  6000 requests in 10.10s, 1.53MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    594.20
Transfer/sec:    155.51KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    61.06ms   1.35s    84.58%
    Req/Sec   135.92    114.04   646.00     69.30%
  13586 requests in 10.04s, 3.47MB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:   1352.95
Transfer/sec:    354.09KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     6.00      0.00     6.00    100.00%
  64 requests in 10.03s, 16.75KB read
  Socket errors: connect 0, read 0, write 0, timeout 64
Requests/sec:      6.38
Transfer/sec:      1.67KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.04s, 0.00B read
  Socket errors: connect 0, read 65, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.25s   479.30ms   1.97s    56.76%
    Req/Sec    23.52     17.75   121.00     76.89%
  3328 requests in 10.11s, 21.27MB read
  Socket errors: connect 0, read 0, write 0, timeout 3180
Requests/sec:    329.28
Transfer/sec:      2.10MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.70s   174.02ms   2.00s    60.69%
    Req/Sec    63.10     54.94   330.00     72.80%
  2542 requests in 10.09s, 16.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 2280
Requests/sec:    251.85
Transfer/sec:      1.61MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.03s   273.16ms   1.96s    69.60%
    Req/Sec     7.07      8.44    50.00     86.59%
  255 requests in 10.10s, 6.22MB read
  Socket errors: connect 0, read 0, write 0, timeout 130
Requests/sec:     25.25
Transfer/sec:    630.59KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
  Socket errors: connect 0, read 6, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s   200.55ms   1.94s    78.12%
    Req/Sec     4.93      8.38    70.00     91.04%
  167 requests in 10.05s, 4.07MB read
  Socket errors: connect 0, read 423, write 0, timeout 103
Requests/sec:     16.62
Transfer/sec:    415.12KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.02s, 0.00B read
  Socket errors: connect 0, read 259, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.46s   281.37ms   1.99s    60.32%
    Req/Sec     9.76      8.61    70.00     70.31%
  514 requests in 10.10s, 12.54MB read
  Socket errors: connect 0, read 0, write 0, timeout 451
Requests/sec:     50.90
Transfer/sec:      1.24MB
```

## Granian Asyncio

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   401.49ms  170.58ms   1.29s    81.60%
    Req/Sec   268.20     77.00   535.00     68.17%
  49893 requests in 10.04s, 13.42MB read
Requests/sec:   4970.54
Transfer/sec:      1.34MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   372.44ms  206.85ms   1.06s    59.65%
    Req/Sec   269.84    121.37   686.00     68.54%
  53153 requests in 10.09s, 14.29MB read
Requests/sec:   5266.40
Transfer/sec:      1.42MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   798.78ms  533.86ms   2.00s    63.27%
    Req/Sec   108.18     64.63   550.00     71.99%
  21169 requests in 10.10s, 24.69MB read
  Socket errors: connect 0, read 0, write 0, timeout 1176
Requests/sec:   2096.10
Transfer/sec:      2.44MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   925.12ms  585.12ms   2.00s    55.57%
    Req/Sec   100.70     69.36   520.00     71.70%
  18982 requests in 10.10s, 22.14MB read
  Socket errors: connect 0, read 0, write 0, timeout 1126
Requests/sec:   1880.12
Transfer/sec:      2.19MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   722.88ms  481.93ms   2.00s    64.15%
    Req/Sec    81.08     49.66   270.00     67.30%
  15379 requests in 10.04s, 45.11MB read
  Socket errors: connect 0, read 0, write 0, timeout 2556
Requests/sec:   1531.30
Transfer/sec:      4.49MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   955.19ms  511.71ms   2.00s    68.04%
    Req/Sec    90.44     62.65   400.00     70.86%
  16576 requests in 10.10s, 48.63MB read
  Socket errors: connect 0, read 0, write 0, timeout 1866
Requests/sec:   1641.29
Transfer/sec:      4.81MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.18s   221.20ms   2.00s    90.53%
    Req/Sec    91.75     67.42   515.00     74.20%
  15737 requests in 10.09s, 4.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 288
Requests/sec:   1559.05
Transfer/sec:    408.03KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.18s   152.86ms   1.72s    61.11%
    Req/Sec    92.14     61.57   474.00     68.52%
  15856 requests in 10.01s, 4.05MB read
Requests/sec:   1583.62
Transfer/sec:    414.46KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   119.97    101.54   470.00     66.05%
  5418 requests in 10.02s, 1.38MB read
  Socket errors: connect 0, read 0, write 0, timeout 5418
Requests/sec:    540.66
Transfer/sec:    141.50KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   131.18ms   1.60s    61.53%
    Req/Sec    99.76     71.12   530.00     76.68%
  16289 requests in 10.09s, 4.16MB read
Requests/sec:   1614.20
Transfer/sec:    422.47KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.04s, 0.00B read
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
  0 requests in 10.05s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   443.78ms   1.99s    74.34%
    Req/Sec    22.60     18.28   130.00     81.59%
  3465 requests in 10.11s, 22.15MB read
  Socket errors: connect 0, read 0, write 0, timeout 3352
Requests/sec:    342.72
Transfer/sec:      2.19MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   768.69ms  539.02ms   2.00s    63.65%
    Req/Sec    51.85     61.41   290.00     85.38%
  1573 requests in 10.10s, 10.05MB read
  Socket errors: connect 0, read 0, write 0, timeout 613
Requests/sec:    155.73
Transfer/sec:      1.00MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.60s   366.80ms   1.85s    80.00%
    Req/Sec     2.38      3.77    20.00     87.36%
  103 requests in 10.09s, 2.25MB read
  Socket errors: connect 0, read 0, write 0, timeout 98
  Non-2xx or 3xx responses: 11
Requests/sec:     10.20
Transfer/sec:    227.92KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.05s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

## Granian uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   415.58ms  230.51ms   1.59s    83.66%
    Req/Sec   264.53     94.27   690.00     70.76%
  48634 requests in 10.04s, 13.08MB read
Requests/sec:   4845.14
Transfer/sec:      1.30MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   373.86ms  248.80ms   1.16s    66.16%
    Req/Sec   269.71    132.09   787.00     67.89%
  53469 requests in 10.04s, 14.38MB read
Requests/sec:   5324.01
Transfer/sec:      1.43MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   643.97ms  432.72ms   1.99s    63.88%
    Req/Sec   149.77     81.94   510.00     67.54%
  29354 requests in 10.10s, 34.24MB read
Requests/sec:   2907.45
Transfer/sec:      3.39MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   853.22ms  653.48ms   2.00s    48.22%
    Req/Sec    96.45     71.80   520.00     70.75%
  18242 requests in 10.10s, 21.28MB read
  Socket errors: connect 0, read 0, write 0, timeout 2081
Requests/sec:   1806.71
Transfer/sec:      2.11MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   774.29ms  583.34ms   2.00s    57.55%
    Req/Sec    87.04     57.45   380.00     72.40%
  16349 requests in 10.09s, 47.96MB read
  Socket errors: connect 0, read 0, write 0, timeout 2094
Requests/sec:   1620.69
Transfer/sec:      4.75MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   949.22ms  403.93ms   2.00s    67.35%
    Req/Sec    90.68     54.79   400.00     72.42%
  17151 requests in 10.10s, 50.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 1609
Requests/sec:   1697.96
Transfer/sec:      4.98MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.25s   246.79ms   2.00s    76.69%
    Req/Sec    91.25     79.07   720.00     75.93%
  15043 requests in 10.09s, 3.84MB read
  Socket errors: connect 0, read 0, write 0, timeout 270
Requests/sec:   1490.97
Transfer/sec:    390.21KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   154.85ms   1.64s    65.84%
    Req/Sec    91.95     69.70   450.00     71.28%
  15458 requests in 10.02s, 3.95MB read
Requests/sec:   1542.59
Transfer/sec:    403.73KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   160.06    124.07   630.00     66.67%
  5645 requests in 10.03s, 1.44MB read
  Socket errors: connect 0, read 0, write 0, timeout 5645
Requests/sec:    563.06
Transfer/sec:    147.36KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.19s   133.78ms   1.59s    62.76%
    Req/Sec    99.31     90.53   660.00     81.82%
  15796 requests in 10.09s, 4.04MB read
Requests/sec:   1564.98
Transfer/sec:    409.58KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    60.50     85.56   121.00    100.00%
  16 requests in 10.10s, 4.19KB read
  Socket errors: connect 0, read 0, write 0, timeout 16
Requests/sec:      1.58
Transfer/sec:     424.57B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     3.50      4.95     7.00    100.00%
  79 requests in 10.10s, 20.68KB read
  Socket errors: connect 0, read 0, write 0, timeout 79
Requests/sec:      7.82
Transfer/sec:      2.05KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.44s   470.51ms   2.00s    69.80%
    Req/Sec    22.76     18.63   190.00     79.71%
  3594 requests in 10.11s, 22.97MB read
  Socket errors: connect 0, read 0, write 0, timeout 3094
Requests/sec:    355.45
Transfer/sec:      2.27MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s   719.89ms   1.87s    54.27%
    Req/Sec    36.63     67.80   343.00     92.06%
  1039 requests in 10.10s, 6.64MB read
  Socket errors: connect 0, read 0, write 0, timeout 746
Requests/sec:    102.87
Transfer/sec:    673.27KB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   978.49ms  529.99ms   1.65s    42.86%
    Req/Sec     2.48      4.13    20.00     84.52%
  106 requests in 10.09s, 2.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 92
  Non-2xx or 3xx responses: 7
Requests/sec:     10.50
Transfer/sec:    245.19KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.05s, 0.00B read
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
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.04s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```
