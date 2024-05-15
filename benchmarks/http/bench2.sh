file="20-urls.md"

echo "Benchmarking HTTP requests"
echo "Async..."

echo "Async" > $file
echo "" >> $file
PYTHON_GIL=0 python async2.py -Xgil=0 >> $file
echo "" >> $file

echo "Sync..."

echo "Sync" >> $file
PYTHON_GIL=0 python sync2.py -Xgil=0 >> $file

echo "Done"
