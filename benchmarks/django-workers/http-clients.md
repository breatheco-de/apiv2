# Django Workers
## WSGI Gunicorn Gevent, 700 connections
### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.30s   364.77ms   1.99s    62.94%
    Req/Sec     6.21      6.42    40.00     91.01%
  466 requests in 10.10s, 11.38MB read
  Socket errors: connect 0, read 0, write 0, timeout 323
Requests/sec:     46.13
Transfer/sec:      1.13MB
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.50s   318.48ms   2.00s    71.64%
    Req/Sec     3.79      4.69    20.00     78.06%
  188 requests in 10.10s, 4.59MB read
  Socket errors: connect 0, read 0, write 0, timeout 121
Requests/sec:     18.61
Transfer/sec:    465.32KB
```

## ASGI Gunicorn Uvicorn, 700 connections
### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.05s   283.72ms   1.90s    60.91%
    Req/Sec     8.70     10.73    60.00     80.88%
  454 requests in 10.09s, 11.07MB read
  Socket errors: connect 0, read 0, write 0, timeout 101
Requests/sec:     45.00
Transfer/sec:      1.10MB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.09s, 0.00B read
  Socket errors: connect 0, read 70, write 0, timeout 0
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.14s   315.70ms   2.00s    80.00%
    Req/Sec     5.85      7.02    40.00     89.88%
  330 requests in 10.10s, 8.05MB read
  Socket errors: connect 0, read 0, write 0, timeout 130
Requests/sec:     32.67
Transfer/sec:    815.97KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     8.11      6.95    30.00     67.57%
  50 requests in 10.09s, 1.22MB read
  Socket errors: connect 0, read 22, write 0, timeout 50
Requests/sec:      4.96
Transfer/sec:    123.77KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.15s   493.78ms   2.00s    54.93%
    Req/Sec     5.67      6.44    40.00     91.84%
  363 requests in 10.10s, 8.85MB read
  Socket errors: connect 0, read 0, write 0, timeout 292
Requests/sec:     35.94
Transfer/sec:      0.88MB
```

## ASGI Hypercorn Uvloop, 700 connections
### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.34s   258.42ms   1.99s    78.46%
    Req/Sec     4.19      5.21    20.00     74.29%
  217 requests in 10.10s, 5.29MB read
  Socket errors: connect 0, read 0, write 0, timeout 152
Requests/sec:     21.48
Transfer/sec:    536.61KB
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
    Latency     1.75s   362.47ms   1.99s    71.43%
    Req/Sec     6.21      7.48    40.00     90.00%
  103 requests in 10.10s, 2.51MB read
  Socket errors: connect 0, read 0, write 0, timeout 96
Requests/sec:     10.20
Transfer/sec:    254.77KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   855.63ms  313.62ms   1.36s    65.22%
    Req/Sec    12.08      9.03    30.00     69.23%
  61 requests in 10.09s, 1.49MB read
  Socket errors: connect 0, read 1, write 0, timeout 15
Requests/sec:      6.04
Transfer/sec:    150.96KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.08s   461.06ms   1.96s    59.48%
    Req/Sec     6.89      6.44    40.00     79.34%
  566 requests in 10.10s, 13.81MB read
  Socket errors: connect 0, read 61, write 0, timeout 450
Requests/sec:     56.05
Transfer/sec:      1.37MB
```

## Granian Uvloop, 700 connections
### Requests
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.10s   293.42ms   1.72s    62.77%
    Req/Sec     4.82      5.76    30.00     95.50%
  271 requests in 10.04s, 6.61MB read
  Socket errors: connect 0, read 0, write 0, timeout 177
Requests/sec:     27.00
Transfer/sec:    674.27KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/requests
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     0.00us    0.00us   0.00us    -nan%
    Req/Sec     0.00      0.00     0.00      -nan%
  0 requests in 10.04s, 0.00B read
Requests/sec:      0.00
Transfer/sec:       0.00B
```

### HTTPX
#### Sync

```bash
Running 10s test @ http://localhost:8000/myapp/sync/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   749.24ms  207.34ms   1.02s    50.00%
    Req/Sec     3.67      5.73    30.00     77.14%
  86 requests in 10.03s, 2.10MB read
  Socket errors: connect 0, read 0, write 0, timeout 48
Requests/sec:      8.58
Transfer/sec:    214.17KB
```

#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/httpx
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.21s   406.82ms   1.94s    60.78%
    Req/Sec     3.73      4.95    20.00     74.64%
  154 requests in 10.02s, 3.76MB read
  Socket errors: connect 0, read 0, write 0, timeout 103
Requests/sec:     15.37
Transfer/sec:    383.91KB
```

### AIOHTTP
#### Async

```bash
Running 10s test @ http://localhost:8000/myapp/async/aiohttp
  20 threads and 700 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency     1.17s   350.33ms   1.96s    65.75%
    Req/Sec     4.41      4.98    20.00     76.53%
  240 requests in 10.03s, 5.85MB read
  Socket errors: connect 0, read 0, write 0, timeout 167
Requests/sec:     23.92
Transfer/sec:    597.48KB
```
