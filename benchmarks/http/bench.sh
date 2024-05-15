file="1000-requests.md"

echo "Benchmarking HTTP requests"
echo "Async..."

echo "Async" > $file
echo "" >> $file
PYTHON_GIL=0 python async.py -Xgil=0 >> $file
echo "" >> $file

echo "Sync..."

echo "Sync" >> $file
PYTHON_GIL=0 python sync.py -Xgil=0 >> $file

echo "Done"
