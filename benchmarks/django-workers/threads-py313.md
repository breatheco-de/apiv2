# Django Workers
## ASGI Gunicorn Uvicorn, with threads -Xgil=0

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   136.35    242.30     0.99k    86.49%
  2000 requests in 10.09s, 550.78KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:    198.31
Transfer/sec:     54.61KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   179.31    276.02     0.91k    83.33%
  2000 requests in 10.05s, 550.78KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:    199.02
Transfer/sec:     54.81KB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.08s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   153.47    254.75     0.87k    79.41%
  2000 requests in 10.07s, 523.44KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:    198.62
Transfer/sec:     51.98KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   175.09    239.35     0.96k    84.06%
  1715 requests in 10.09s, 448.85KB read
  Socket errors: connect 0, read 0, write 0, timeout 1715
Requests/sec:    169.98
Transfer/sec:     44.49KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.08s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
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
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.10      0.32     1.00     90.00%
  10 requests in 10.06s, 65.45KB read
  Socket errors: connect 0, read 0, write 0, timeout 10
Requests/sec:      0.99
Transfer/sec:      6.50KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.05s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

## ASGI Gunicorn Uvicorn, with threads -Xgil=1

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   186.82    273.64   830.00     78.75%
  2000 requests in 10.07s, 550.78KB read
  Socket errors: connect 0, read 0, write 0, timeout 2000
Requests/sec:    198.58
Transfer/sec:     54.69KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.07s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.05s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.10s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.05s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.06s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.08s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.07s, 0.00B read
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
  0 requests in 10.03s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.11s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 2000, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

## ASGI Gunicorn Uvicorn, with workers -Xgil=0

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   178.74ms  339.44ms   2.00s    93.94%
    Req/Sec   383.85    379.53     1.18k    70.97%
  28846 requests in 10.10s, 7.76MB read
  Socket errors: connect 0, read 0, write 0, timeout 2256
Requests/sec:   2856.05
Transfer/sec:    786.55KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   698.98ms  384.09ms   1.98s    69.18%
    Req/Sec   148.62    121.28     1.67k    73.84%
  27942 requests in 10.06s, 7.51MB read
  Socket errors: connect 0, read 0, write 0, timeout 112
Requests/sec:   2776.16
Transfer/sec:    764.55KB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   879.42ms  533.47ms   2.00s    54.36%
    Req/Sec   107.06     93.71   600.00     78.11%
  20292 requests in 10.08s, 4.90MB read
  Socket errors: connect 0, read 0, write 0, timeout 948
Requests/sec:   2013.20
Transfer/sec:    497.43KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   957.97ms  309.21ms   1.85s    71.55%
    Req/Sec   113.84    124.82   660.00     86.43%
  16727 requests in 10.10s, 4.04MB read
  Socket errors: connect 0, read 0, write 0, timeout 1428
Requests/sec:   1656.08
Transfer/sec:    409.19KB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.13s   314.86ms   1.96s    64.61%
    Req/Sec    87.98     88.27   730.00     86.57%
  14841 requests in 10.10s, 8.14MB read
  Socket errors: connect 0, read 0, write 0, timeout 1182
Requests/sec:   1470.13
Transfer/sec:    825.54KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   946.53ms  420.16ms   2.00s    78.18%
    Req/Sec   100.77    112.74   727.00     86.11%
  14171 requests in 10.08s, 7.77MB read
  Socket errors: connect 0, read 0, write 0, timeout 3069
Requests/sec:   1405.21
Transfer/sec:    789.06KB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.45s   262.79ms   2.00s    59.58%
    Req/Sec    97.63    113.74   800.00     86.95%
  11344 requests in 10.10s, 2.90MB read
  Socket errors: connect 0, read 0, write 0, timeout 2651
Requests/sec:   1123.38
Transfer/sec:    294.01KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.42s   244.45ms   2.00s    68.50%
    Req/Sec    92.13    104.20     0.91k    87.93%
  12180 requests in 10.10s, 3.11MB read
  Socket errors: connect 0, read 0, write 0, timeout 1337
Requests/sec:   1206.22
Transfer/sec:    315.69KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   106.23    141.99     0.86k    87.46%
  4721 requests in 10.06s, 1.21MB read
  Socket errors: connect 0, read 0, write 0, timeout 4721
Requests/sec:    469.39
Transfer/sec:    122.87KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.35s   212.12ms   1.94s    70.02%
    Req/Sec    85.03     86.76   737.00     91.33%
  13657 requests in 10.10s, 3.49MB read
  Socket errors: connect 0, read 0, write 0, timeout 176
Requests/sec:   1352.33
Transfer/sec:    353.93KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   145.50    282.27   717.00     83.33%
  157 requests in 10.05s, 41.09KB read
  Socket errors: connect 0, read 0, write 0, timeout 157
Requests/sec:     15.63
Transfer/sec:      4.09KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00    100.00%
  5 requests in 10.10s, 1.31KB read
  Socket errors: connect 0, read 0, write 0, timeout 5
Requests/sec:      0.50
Transfer/sec:     132.68B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.43s   409.09ms   2.00s    68.74%
    Req/Sec    24.95     27.19   210.00     89.87%
  3057 requests in 10.10s, 19.54MB read
  Socket errors: connect 0, read 172, write 0, timeout 2190
Requests/sec:    302.78
Transfer/sec:      1.94MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.36s   405.31ms   1.95s    61.58%
    Req/Sec    31.40    104.70     0.92k    97.06%
  1287 requests in 10.09s, 8.23MB read
  Socket errors: connect 0, read 1142, write 0, timeout 920
Requests/sec:    127.49
Transfer/sec:    834.41KB
```

## ASGI Gunicorn Uvicorn, with workers -Xgil=1

### JSON performance
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   552.16ms  366.20ms   2.00s    80.77%
    Req/Sec   113.62    102.55   740.00     76.80%
  18140 requests in 10.10s, 4.88MB read
  Socket errors: connect 0, read 0, write 0, timeout 4102
Requests/sec:   1796.89
Transfer/sec:    494.87KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   806.98ms  418.05ms   2.00s    62.49%
    Req/Sec   102.03     94.98   580.00     78.75%
  15685 requests in 10.09s, 4.22MB read
  Socket errors: connect 0, read 0, write 0, timeout 1028
Requests/sec:   1554.58
Transfer/sec:    428.19KB
```

### Queries returned as JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.09s   604.32ms   2.00s    56.31%
    Req/Sec    63.52     59.24   450.00     82.75%
  9382 requests in 10.06s, 2.26MB read
  Socket errors: connect 0, read 0, write 0, timeout 2097
Requests/sec:    932.46
Transfer/sec:    230.38KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.25s   471.66ms   2.00s    66.91%
    Req/Sec    65.14     62.76   464.00     83.21%
  10158 requests in 10.04s, 2.45MB read
  Socket errors: connect 0, read 0, write 0, timeout 3876
Requests/sec:   1011.50
Transfer/sec:    249.96KB
```

### Queries returned as HTML
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.33s   483.35ms   2.00s    66.95%
    Req/Sec    41.79     37.81   525.00     86.85%
  6981 requests in 10.10s, 3.83MB read
  Socket errors: connect 0, read 0, write 0, timeout 2806
Requests/sec:    691.23
Transfer/sec:    388.17KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.36s   403.77ms   2.00s    65.89%
    Req/Sec    55.69     61.10   383.00     86.28%
  7921 requests in 10.06s, 4.34MB read
  Socket errors: connect 0, read 0, write 0, timeout 3978
Requests/sec:    787.03
Transfer/sec:    441.94KB
```

### Simulate a request 1s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.49s   245.81ms   2.00s    66.50%
    Req/Sec    66.44     74.91   490.00     89.22%
  9192 requests in 10.07s, 2.35MB read
  Socket errors: connect 0, read 0, write 0, timeout 3380
Requests/sec:    912.86
Transfer/sec:    238.94KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.44s   269.68ms   2.00s    60.46%
    Req/Sec    67.22     70.76   590.00     86.94%
  10597 requests in 10.08s, 2.71MB read
  Socket errors: connect 0, read 0, write 0, timeout 2774
Requests/sec:   1051.56
Transfer/sec:    275.21KB
```

### Simulate a request 3s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec    65.69     78.46   505.00     88.74%
  4381 requests in 10.05s, 1.12MB read
  Socket errors: connect 0, read 0, write 0, timeout 4381
Requests/sec:    436.10
Transfer/sec:    114.14KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.48s   236.21ms   2.00s    63.70%
    Req/Sec    62.13     70.03   530.00     88.32%
  9284 requests in 10.07s, 2.37MB read
  Socket errors: connect 0, read 0, write 0, timeout 3064
Requests/sec:    922.30
Transfer/sec:    241.41KB
```

### Simulate a request 10s inside the server, then return a JSON
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     2.00      0.82     3.00     50.00%
  94 requests in 10.10s, 25.09KB read
  Socket errors: connect 0, read 0, write 0, timeout 94
Requests/sec:      9.30
Transfer/sec:      2.48KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00    100.00%
  3 requests in 10.08s, 804.00B read
  Socket errors: connect 0, read 0, write 0, timeout 3
Requests/sec:      0.30
Transfer/sec:      79.74B
```

### Brotli
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.17s   540.89ms   2.00s    57.58%
    Req/Sec    22.56     30.03   363.00     90.41%
  2575 requests in 10.10s, 16.46MB read
  Socket errors: connect 0, read 0, write 0, timeout 1948
Requests/sec:    254.92
Transfer/sec:      1.63MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   975.61ms  236.78ms   1.56s    72.91%
    Req/Sec    45.34     69.98   434.00     91.47%
  1384 requests in 10.09s, 8.85MB read
  Socket errors: connect 0, read 1144, write 0, timeout 775
Requests/sec:    137.11
Transfer/sec:      0.88MB
```
