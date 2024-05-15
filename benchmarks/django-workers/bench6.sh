# trio is not supported by django yet and should break gevent

FILE="./threads-py313.md"
CONNECTIONS=2000
THREADS=20
PORT=8000
HOST="http://localhost:$PORT"
TIMEOUT=10
SLEEP_TIME=3


# it support wsgi and asgi
function bench {
    HOST="http://localhost:8000"

    echo "" >> "$FILE"
    echo "### JSON performance" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/json" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/json" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    echo "### Queries returned as JSON" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/json_query" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/json_query" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    echo "### Queries returned as HTML" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/template_query" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/template_query" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    echo "### Simulate a request 1s inside the server, then return a JSON" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/gateway_1s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/gateway_1s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    sleep $SLEEP_TIME

    echo "### Simulate a request 3s inside the server, then return a JSON" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/gateway_3s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/gateway_3s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    sleep $SLEEP_TIME

    echo "### Simulate a request 10s inside the server, then return a JSON" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/gateway_10s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/gateway_10s" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    sleep $SLEEP_TIME

    echo "### Brotli" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/brotli" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/brotli" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
}


echo "# Django Workers" > $FILE

sudo fuser -k $PORT/tcp
PYTHON_GIL=0 python -Xgil=0 -m gunicorn mysite.asgi --timeout $TIMEOUT --threads $THREADS --worker-class uvicorn.workers.UvicornWorker & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Gunicorn Uvicorn, with threads -Xgil=0" >> $FILE
bench

sudo fuser -k $PORT/tcp
PYTHON_GIL=1 python -Xgil=1 -m gunicorn mysite.asgi --timeout $TIMEOUT --threads $THREADS --worker-class uvicorn.workers.UvicornWorker & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Gunicorn Uvicorn, with threads -Xgil=1" >> $FILE
bench

sudo fuser -k $PORT/tcp
PYTHON_GIL=0 python -Xgil=0 -m gunicorn mysite.asgi --timeout $TIMEOUT --workers $THREADS --worker-class uvicorn.workers.UvicornWorker & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Gunicorn Uvicorn, with workers -Xgil=0" >> $FILE
bench

sudo fuser -k $PORT/tcp
PYTHON_GIL=1 python -Xgil=1 -m gunicorn mysite.asgi --timeout $TIMEOUT --workers $THREADS --worker-class uvicorn.workers.UvicornWorker & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Gunicorn Uvicorn, with workers -Xgil=1" >> $FILE
bench


sudo fuser -k $PORT/tcp
