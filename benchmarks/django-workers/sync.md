# Django Workers

## WSGI Gunicorn Gevent

### JSON performance

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   297.27ms  474.88ms   2.00s    82.70%
    Req/Sec     1.75k     1.13k   20.79k    84.22%
  322165 requests in 10.10s, 94.33MB read
  Socket errors: connect 0, read 0, write 0, timeout 2301
Requests/sec:  31896.61
Transfer/sec:      9.34MB
```

### Queries returned as JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    80.14ms  212.35ms   2.00s    88.27%
    Req/Sec     1.59k     0.86k    6.99k    73.10%
  120660 requests in 10.09s, 143.61MB read
  Socket errors: connect 0, read 0, write 0, timeout 241
Requests/sec:  11958.97
Transfer/sec:     14.23MB
```

### Queries returned as HTML

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    64.06ms  202.17ms   1.96s    90.36%
    Req/Sec     1.46k   709.59     3.40k    66.79%
  77158 requests in 10.09s, 228.18MB read
  Socket errors: connect 0, read 0, write 0, timeout 213
Requests/sec:   7646.02
Transfer/sec:     22.61MB
```

### Simulate a request 1s inside the server, then return a JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.02s    44.46ms   1.24s    94.37%
    Req/Sec   181.12    246.38     0.94k    82.93%
  16956 requests in 10.10s, 4.74MB read
Requests/sec:   1679.09
Transfer/sec:    480.44KB
```

### Simulate a request 3s inside the server, then return a JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   271.84    406.57     1.00k    73.56%
  6000 requests in 10.08s, 1.68MB read
  Socket errors: connect 0, read 0, write 0, timeout 6000
Requests/sec:    595.01
Transfer/sec:    170.25KB
```

### Simulate a request 10s inside the server, then return a JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_10s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec   247.93    345.63     0.92k    75.00%
  1224 requests in 10.10s, 351.58KB read
  Socket errors: connect 0, read 0, write 0, timeout 1224
Requests/sec:    121.23
Transfer/sec:     34.82KB
```

### Brotli

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/brotli
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    52.34ms   89.73ms   1.96s    99.44%
    Req/Sec    53.55     32.99   191.00     64.65%
  4348 requests in 10.09s, 27.89MB read
  Socket errors: connect 0, read 0, write 0, timeout 68
Requests/sec:    430.81
Transfer/sec:      2.76MB
```

### Requests

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.23s   397.46ms   1.94s    64.71%
    Req/Sec     8.02      9.49    70.00     84.75%
  353 requests in 10.10s, 8.62MB read
  Socket errors: connect 0, read 0, write 0, timeout 319
Requests/sec:     34.96
Transfer/sec:      0.85MB
```

### HTTPX

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.93s     0.00us   1.93s   100.00%
    Req/Sec     2.21      3.50    20.00     89.36%
  103 requests in 10.09s, 2.51MB read
  Socket errors: connect 0, read 0, write 0, timeout 102
Requests/sec:     10.20
Transfer/sec:    255.10KB
```

## WSGI Granian

### JSON performance

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency    50.43ms   56.81ms 601.79ms   95.22%
    Req/Sec     2.47k   584.79     7.55k    72.33%
  476131 requests in 10.10s, 128.05MB read
Requests/sec:  47134.70
Transfer/sec:     12.68MB
```

### Queries returned as JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/json_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   198.68ms   48.66ms 399.29ms   77.45%
    Req/Sec   500.29    114.02     1.36k    70.49%
  99743 requests in 10.09s, 116.33MB read
Requests/sec:   9882.84
Transfer/sec:     11.53MB
```

### Queries returned as HTML

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/template_query
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   319.61ms  147.51ms 881.80ms   76.25%
    Req/Sec   313.39    120.39   686.00     66.57%
  62635 requests in 10.09s, 183.74MB read
Requests/sec:   6206.26
Transfer/sec:     18.21MB
```

### Simulate a request 1s inside the server, then return a JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_1s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.17s   208.24ms   1.99s    90.48%
    Req/Sec     9.55     13.87    80.00     92.45%
  191 requests in 10.09s, 49.99KB read
  Socket errors: connect 0, read 0, write 0, timeout 170
Requests/sec:     18.92
Transfer/sec:      4.95KB
```

### Simulate a request 3s inside the server, then return a JSON

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/gateway_3s
  20 threads and 2000 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.03s, 0.00B read
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
  0 requests in 10.03s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### Requests

#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
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
Requests/sec:      0.00
Transfer/sec:       0.00B
```
