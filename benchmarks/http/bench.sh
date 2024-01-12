file="README.md"

echo "Benchmarking HTTP requests"
echo "Async..."

echo "Async" > $file
echo "" >> $file
python async.py >> $file
echo "" >> $file

echo "Sync..."

echo "Sync" >> $file
python sync.py >> $file

echo "Done"
