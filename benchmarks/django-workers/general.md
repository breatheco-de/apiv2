# Django Workers
## WSGI Gunicorn Gevent

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   266.45ms  430.37ms   2.00s    82.98%
    Req/Sec     1.73k     0.94k   12.92k    79.29%
  320765 requests in 10.03s, 93.92MB read
  Socket errors: connect 0, read 0, write 0, timeout 1856
Requests/sec:  31967.83
Transfer/sec:      9.36MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    79.65ms  217.57ms   1.99s    88.71%
    Req/Sec     1.43k     0.91k    7.38k    73.86%
  118770 requests in 10.09s, 141.36MB read
  Socket errors: connect 0, read 0, write 0, timeout 229
Requests/sec:  11767.12
Transfer/sec:     14.01MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    68.00ms  229.69ms   2.00s    91.42%
    Req/Sec     0.90k   717.69     7.55k    78.45%
  75847 requests in 10.09s, 224.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 183
Requests/sec:   7520.05
Transfer/sec:     22.24MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    46.42ms   1.25s    94.61%
    Req/Sec   212.14    213.43     0.86k    80.72%
  16938 requests in 10.05s, 4.73MB read
Requests/sec:   1684.79
Transfer/sec:    482.13KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   265.27    390.49     1.00k    73.64%
  8653 requests in 15.10s, 2.42MB read
  Socket errors: connect 0, read 0, write 0, timeout 8653
Requests/sec:    573.02
Transfer/sec:    163.98KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   288.61    375.76     0.99k    75.36%
  4000 requests in 22.05s, 1.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.37
Transfer/sec:     51.90KB
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    51.78ms   78.69ms   1.98s    99.48%
    Req/Sec    52.53     42.60   252.00     83.00%
  4290 requests in 10.10s, 27.52MB read
  Socket errors: connect 0, read 0, write 0, timeout 77
Requests/sec:    424.79
Transfer/sec:      2.73MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   109.79ms  107.04ms   1.27s    88.28%
    Req/Sec     1.12k   412.21     2.30k    62.63%
  221726 requests in 10.10s, 61.96MB read
Requests/sec:  21956.55
Transfer/sec:      6.14MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   204.28ms   10.31ms 334.70ms   94.22%
    Req/Sec   489.34    252.24     1.00k    64.35%
  97463 requests in 10.10s, 27.24MB read
Requests/sec:   9649.85
Transfer/sec:      2.70MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   489.01ms   2.00s    64.80%
    Req/Sec     5.52      6.68    50.00     93.96%
  432 requests in 10.10s, 10.55MB read
  Socket errors: connect 0, read 0, write 0, timeout 307
Requests/sec:     42.77
Transfer/sec:      1.04MB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.75s     0.00us   1.75s   100.00%
    Req/Sec     2.19      4.35    20.00     88.71%
  68 requests in 10.09s, 1.66MB read
  Socket errors: connect 0, read 0, write 0, timeout 67
Requests/sec:      6.74
Transfer/sec:    168.43KB
```

## ASGI Gunicorn Uvicorn

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   415.75ms  134.28ms   1.49s    91.75%
    Req/Sec   254.69     73.48   600.00     70.50%
  47871 requests in 10.10s, 12.87MB read
Requests/sec:   4741.47
Transfer/sec:      1.28MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   445.30ms  135.68ms   1.07s    72.31%
    Req/Sec   222.30     89.69   750.00     73.83%
  43840 requests in 10.06s, 11.79MB read
Requests/sec:   4359.84
Transfer/sec:      1.17MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   911.18ms  197.45ms   2.00s    85.77%
    Req/Sec   110.66     54.96   430.00     72.69%
  20980 requests in 10.10s, 24.47MB read
  Socket errors: connect 0, read 0, write 0, timeout 30
Requests/sec:   2077.47
Transfer/sec:      2.42MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   916.79ms  193.48ms   2.00s    85.99%
    Req/Sec   111.20     50.40   435.00     71.63%
  20719 requests in 10.03s, 24.17MB read
  Socket errors: connect 0, read 0, write 0, timeout 91
Requests/sec:   2065.30
Transfer/sec:      2.41MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   263.03ms   2.00s    77.27%
    Req/Sec    88.68     46.01   410.00     72.98%
  16430 requests in 10.09s, 48.20MB read
  Socket errors: connect 0, read 0, write 0, timeout 545
Requests/sec:   1628.06
Transfer/sec:      4.78MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   994.88ms  195.12ms   2.00s    84.58%
    Req/Sec   100.63     47.91   440.00     69.91%
  18794 requests in 10.09s, 55.13MB read
  Socket errors: connect 0, read 0, write 0, timeout 254
Requests/sec:   1862.59
Transfer/sec:      5.46MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.07s   115.52ms   1.58s    87.82%
    Req/Sec   154.94    173.58     0.87k    85.45%
  17818 requests in 10.10s, 4.55MB read
Requests/sec:   1764.02
Transfer/sec:    461.68KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.12s   254.47ms   2.00s    89.26%
    Req/Sec   135.85    117.70   653.00     66.81%
  16794 requests in 10.03s, 4.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 220
Requests/sec:   1674.72
Transfer/sec:    438.31KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   151.98    150.28   840.00     71.81%
  8000 requests in 15.03s, 2.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 8000
Requests/sec:    532.18
Transfer/sec:    139.28KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   202.59ms   1.99s    92.07%
    Req/Sec   112.90     96.30   676.00     77.00%
  26095 requests in 15.10s, 6.67MB read
Requests/sec:   1728.59
Transfer/sec:    452.40KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 22s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   174.53    154.87   640.00     58.76%
  4000 requests in 22.04s, 1.02MB read
  Socket errors: connect 0, read 0, write 0, timeout 4000
Requests/sec:    181.48
Transfer/sec:     47.50KB
```

#### Async

```bash
Running 22s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   127.23    160.73   630.00     80.17%
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
    Latency     1.42s   371.60ms   1.93s    58.62%
    Req/Sec    26.08     23.06   171.00     79.84%
  3310 requests in 10.10s, 21.16MB read
  Socket errors: connect 0, read 0, write 0, timeout 3281
Requests/sec:    327.59
Transfer/sec:      2.09MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.75s   131.77ms   2.00s    62.50%
    Req/Sec    56.34     46.54   313.00     76.18%
  1999 requests in 10.09s, 12.78MB read
  Socket errors: connect 0, read 0, write 0, timeout 1791
Requests/sec:    198.10
Transfer/sec:      1.27MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   535.83ms  139.21ms   1.11s    70.31%
    Req/Sec   185.62     66.67   610.00     78.73%
  36322 requests in 10.10s, 9.28MB read
Requests/sec:   3597.41
Transfer/sec:      0.92MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   536.33ms  132.15ms   1.48s    76.64%
    Req/Sec   188.86     68.62     0.90k    76.73%
  36429 requests in 10.09s, 9.31MB read
Requests/sec:   3609.18
Transfer/sec:      0.92MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   555.32ms  112.69ms   1.17s    70.36%
    Req/Sec   182.79     72.01   600.00     75.41%
  35055 requests in 10.09s, 8.96MB read
Requests/sec:   3473.68
Transfer/sec:      0.89MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   553.52ms  138.65ms   1.48s    72.70%
    Req/Sec   184.62     65.40   400.00     71.45%
  35154 requests in 10.10s, 8.98MB read
Requests/sec:   3480.11
Transfer/sec:      0.89MB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   844.86ms  206.01ms   1.17s    61.84%
    Req/Sec     4.90      6.33    30.00     91.67%
  184 requests in 10.10s, 4.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 108
Requests/sec:     18.22
Transfer/sec:    454.97KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 1, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.45s   203.23ms   1.80s    74.07%
    Req/Sec     4.20      6.56    50.00     95.15%
  204 requests in 10.10s, 4.98MB read
  Socket errors: connect 0, read 4, write 0, timeout 177
Requests/sec:     20.20
Transfer/sec:    504.39KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.30      0.67     2.00     80.00%
  11 requests in 10.03s, 274.71KB read
  Socket errors: connect 0, read 258, write 0, timeout 11
Requests/sec:      1.10
Transfer/sec:     27.39KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.24s   333.65ms   1.96s    66.67%
    Req/Sec     7.18      6.45    50.00     78.55%
  558 requests in 10.10s, 13.61MB read
  Socket errors: connect 0, read 25, write 0, timeout 480
Requests/sec:     55.24
Transfer/sec:      1.35MB
```

## ASGI Hypercorn Asyncio

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   492.55ms  204.94ms   1.35s    73.18%
    Req/Sec   208.78     94.33   620.00     70.59%
  39728 requests in 10.10s, 10.89MB read
Requests/sec:   3933.42
Transfer/sec:      1.08MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   591.43ms  355.42ms   1.84s    70.89%
    Req/Sec   165.89     98.88   727.00     70.86%
  32330 requests in 10.10s, 8.86MB read
Requests/sec:   3201.18
Transfer/sec:      0.88MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   981.57ms  445.13ms   2.00s    69.00%
    Req/Sec    87.44     58.90   410.00     71.79%
  16287 requests in 10.10s, 19.08MB read
  Socket errors: connect 0, read 0, write 0, timeout 1043
Requests/sec:   1612.28
Transfer/sec:      1.89MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s   430.42ms   2.00s    65.90%
    Req/Sec    88.24     64.11   590.00     76.23%
  16138 requests in 10.10s, 18.90MB read
  Socket errors: connect 0, read 0, write 0, timeout 559
Requests/sec:   1598.16
Transfer/sec:      1.87MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   468.03ms   2.00s    67.59%
    Req/Sec    70.26     40.36   390.00     75.21%
  13755 requests in 10.10s, 40.41MB read
  Socket errors: connect 0, read 0, write 0, timeout 1291
Requests/sec:   1362.06
Transfer/sec:      4.00MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   992.65ms  441.41ms   2.00s    65.46%
    Req/Sec    83.32     63.80   616.00     75.96%
  14959 requests in 10.09s, 43.96MB read
  Socket errors: connect 0, read 0, write 0, timeout 823
Requests/sec:   1482.72
Transfer/sec:      4.36MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.14s   122.13ms   1.67s    86.26%
    Req/Sec    98.72     81.71   626.00     76.56%
  15703 requests in 10.10s, 4.10MB read
Requests/sec:   1554.66
Transfer/sec:    415.31KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   127.53ms   1.99s    87.81%
    Req/Sec   102.05     79.02   616.00     72.67%
  14375 requests in 10.10s, 3.76MB read
Requests/sec:   1423.64
Transfer/sec:    380.88KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    85.67     84.58   550.00     78.00%
  8000 requests in 15.10s, 2.08MB read
  Socket errors: connect 0, read 0, write 0, timeout 8000
Requests/sec:    529.77
Transfer/sec:    140.72KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.10s    89.32ms   1.90s    89.91%
    Req/Sec   105.68     85.87   717.00     72.94%
  22379 requests in 15.10s, 5.82MB read
  Socket errors: connect 0, read 0, write 0, timeout 101
Requests/sec:   1482.36
Transfer/sec:    394.99KB
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
  Socket errors: connect 0, read 4000, write 0, timeout 0
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
  0 requests in 22.04s, 0.00B read
  Socket errors: connect 0, read 1831, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.11s   504.85ms   2.00s    61.52%
    Req/Sec    23.54     20.24   130.00     78.15%
  3425 requests in 10.11s, 21.91MB read
  Socket errors: connect 0, read 0, write 0, timeout 2544
Requests/sec:    338.63
Transfer/sec:      2.17MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.39s   379.84ms   1.90s    64.85%
    Req/Sec    63.56     91.60   600.00     88.03%
  1587 requests in 10.09s, 10.15MB read
  Socket errors: connect 0, read 0, write 0, timeout 1092
Requests/sec:    157.22
Transfer/sec:      1.01MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   626.12ms  289.48ms   1.98s    69.94%
    Req/Sec   147.64     71.17   490.00     69.88%
  29219 requests in 10.05s, 7.60MB read
  Socket errors: connect 0, read 0, write 0, timeout 171
Requests/sec:   2907.00
Transfer/sec:    773.99KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   604.39ms  354.09ms   1.85s    75.24%
    Req/Sec   150.10     90.53   848.00     70.61%
  29379 requests in 10.10s, 7.66MB read
Requests/sec:   2908.53
Transfer/sec:    776.51KB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   680.12ms  269.05ms   1.73s    71.82%
    Req/Sec   141.98     81.39   770.00     71.23%
  26696 requests in 10.10s, 6.95MB read
Requests/sec:   2644.40
Transfer/sec:    704.97KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   634.29ms  226.44ms   1.47s    67.05%
    Req/Sec   145.86     70.82   620.00     70.80%
  26868 requests in 10.10s, 7.00MB read
Requests/sec:   2660.41
Transfer/sec:    709.62KB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   305.24ms   1.66s    56.86%
    Req/Sec     4.05      5.41    20.00     75.76%
  173 requests in 10.10s, 4.22MB read
  Socket errors: connect 0, read 0, write 0, timeout 122
Requests/sec:     17.13
Transfer/sec:    427.81KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 2000 connections
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
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.03s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
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
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.03s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

## ASGI Hypercorn Uvloop

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   258.42ms   97.24ms   1.40s    84.32%
    Req/Sec   241.21    139.65   732.00     66.05%
  45891 requests in 10.10s, 12.52MB read
  Socket errors: connect 0, read 0, write 0, timeout 360
Requests/sec:   4545.56
Transfer/sec:      1.24MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   247.25ms  105.59ms   1.99s    77.01%
    Req/Sec   244.24    134.72     1.01k    69.08%
  48711 requests in 10.03s, 13.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 384
Requests/sec:   4854.45
Transfer/sec:      1.32MB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   362.83ms  159.65ms   1.65s    70.88%
    Req/Sec   163.00    102.02   626.00     67.09%
  32336 requests in 10.10s, 37.84MB read
  Socket errors: connect 0, read 0, write 0, timeout 392
Requests/sec:   3201.43
Transfer/sec:      3.75MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   201.88ms   79.60ms 553.30ms   70.43%
    Req/Sec   171.12    126.10     1.05k    76.72%
  34005 requests in 10.10s, 39.79MB read
  Socket errors: connect 0, read 162, write 0, timeout 0
Requests/sec:   3367.22
Transfer/sec:      3.94MB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   700.97ms  434.16ms   2.00s    61.56%
    Req/Sec   103.21     72.27   510.00     76.46%
  20398 requests in 10.09s, 59.92MB read
  Socket errors: connect 0, read 0, write 0, timeout 561
Requests/sec:   2021.20
Transfer/sec:      5.94MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   550.07ms  283.50ms   2.00s    64.54%
    Req/Sec   108.22    108.83     1.22k    91.53%
  18525 requests in 10.09s, 54.41MB read
  Socket errors: connect 0, read 0, write 0, timeout 577
Requests/sec:   1836.20
Transfer/sec:      5.39MB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s    48.60ms   1.31s    92.22%
    Req/Sec   112.97    122.43   820.00     86.80%
  12779 requests in 10.09s, 3.31MB read
  Socket errors: connect 0, read 0, write 0, timeout 383
Requests/sec:   1266.01
Transfer/sec:    336.28KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.06s   116.65ms   2.00s    94.65%
    Req/Sec    96.98    111.26     0.95k    86.78%
  10095 requests in 10.09s, 2.62MB read
  Socket errors: connect 0, read 0, write 0, timeout 528
Requests/sec:   1000.04
Transfer/sec:    265.64KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 15s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    71.71    116.88     0.86k    89.23%
  7083 requests in 15.10s, 1.84MB read
  Socket errors: connect 0, read 0, write 0, timeout 7083
Requests/sec:    469.12
Transfer/sec:    124.61KB
```

#### Async

```bash
Running 15s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.04s    39.06ms   1.33s    87.94%
    Req/Sec   106.96    100.05   780.00     80.23%
  19008 requests in 15.10s, 4.93MB read
  Socket errors: connect 0, read 0, write 0, timeout 1179
Requests/sec:   1258.93
Transfer/sec:    334.40KB
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
  Socket errors: connect 0, read 3232, write 0, timeout 0
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
  Socket errors: connect 0, read 679, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.64s   380.07ms   2.00s    87.01%
    Req/Sec    23.61     19.12   131.00     75.23%
  3403 requests in 10.10s, 21.76MB read
  Socket errors: connect 0, read 0, write 0, timeout 2941
Requests/sec:    336.88
Transfer/sec:      2.15MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.22s   437.57ms   2.00s    64.85%
    Req/Sec    31.78     30.69   297.00     81.27%
  3303 requests in 10.07s, 21.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 2495
Requests/sec:    327.93
Transfer/sec:      2.10MB
```


### Fake redis hit
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   285.25ms   99.13ms 646.10ms   64.74%
    Req/Sec   202.20    152.20     0.90k    69.69%
  39482 requests in 10.10s, 10.24MB read
  Socket errors: connect 0, read 0, write 0, timeout 215
Requests/sec:   3909.93
Transfer/sec:      1.01MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_hit
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   382.23ms  160.06ms   1.50s    73.49%
    Req/Sec   177.90    114.02   830.00     72.41%
  35040 requests in 10.10s, 9.09MB read
  Socket errors: connect 0, read 0, write 0, timeout 370
Requests/sec:   3469.15
Transfer/sec:      0.90MB
```

### Fake cache set
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   367.11ms   85.50ms 716.77ms   66.34%
    Req/Sec   160.52     91.02   600.00     70.53%
  31122 requests in 10.10s, 8.07MB read
  Socket errors: connect 0, read 105, write 0, timeout 214
Requests/sec:   3082.12
Transfer/sec:    818.69KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/cache_set
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   466.40ms  139.72ms   1.54s    71.00%
    Req/Sec   169.13     86.43   570.00     67.97%
  31428 requests in 10.10s, 8.15MB read
  Socket errors: connect 0, read 0, write 0, timeout 255
Requests/sec:   3111.55
Transfer/sec:    826.51KB
```

### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.35s   207.25ms   1.71s    54.55%
    Req/Sec     3.73      6.06    40.00     76.92%
  173 requests in 10.10s, 4.22MB read
  Socket errors: connect 0, read 0, write 0, timeout 118
Requests/sec:     17.13
Transfer/sec:    427.80KB
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
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
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
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.18s   425.74ms   1.98s    63.56%
    Req/Sec     9.51      7.90    50.00     70.53%
  548 requests in 10.03s, 13.37MB read
  Socket errors: connect 0, read 0, write 0, timeout 312
Requests/sec:     54.62
Transfer/sec:      1.33MB
```
