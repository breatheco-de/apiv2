# trio is not supported by django yet and should break gevent

FILE="./cache.md"
CONNECTIONS=2000
THREADS=20
PORT=8000
HOST="http://localhost:$PORT"
TIMEOUT=60
SLEEP_TIME=3

# it support wsgi
function sync_bench {
    HOST="http://localhost:8000"

    echo "" >> "$FILE"
    echo "### Fake redis hit" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/cache_hit" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    echo "### Fake cache set" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/cache_set" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
}

# it support wsgi and asgi
function bench {
    HOST="http://localhost:8000"

    echo "" >> "$FILE"
    echo "### Fake redis hit" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/cache_hit" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/cache_hit" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"

    echo "### Fake cache set" >> "$FILE"
    echo "#### Sync" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/sync/cache_set" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
    echo "#### Async" >> "$FILE"
    echo "" >> "$FILE"
    echo "\`\`\`bash" >> "$FILE"
    wrk -t "$THREADS" -c "$CONNECTIONS" -d10s "$HOST/myapp/async/cache_set" >> "$FILE"
    echo "\`\`\`" >> "$FILE"
    echo "" >> "$FILE"
}

echo "# Django Workers" > $FILE

sudo fuser -k $PORT/tcp
gunicorn mysite.wsgi --timeout $TIMEOUT --workers $THREADS --worker-class gevent & echo "starting server..."
sleep $SLEEP_TIME
# it is failing
curl -s "$HOST/myapp/async/seed"
echo "## WSGI Gunicorn Gevent" >> $FILE
sync_bench

sudo fuser -k $PORT/tcp
gunicorn mysite.asgi --timeout $TIMEOUT --workers $THREADS --worker-class uvicorn.workers.UvicornWorker & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Gunicorn Uvicorn" >> $FILE
bench

sudo fuser -k $PORT/tcp
hypercorn mysite.asgi:application -b 127.0.0.1:$PORT -w $THREADS --read-timeout $TIMEOUT -k asyncio & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Hypercorn Asyncio" >> $FILE
bench

sudo fuser -k $PORT/tcp
hypercorn mysite.asgi:application -b 127.0.0.1:$PORT -w $THREADS --read-timeout $TIMEOUT -k uvloop & echo "starting server..."
sleep $SLEEP_TIME
echo "## ASGI Hypercorn Uvloop" >> $FILE
bench

sudo fuser -k $PORT/tcp
