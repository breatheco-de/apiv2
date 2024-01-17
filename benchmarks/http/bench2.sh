file="20-urls.md"

echo "Benchmarking HTTP requests"
echo "Async..."

echo "Async" > $file
echo "" >> $file
python async2.py >> $file
echo "" >> $file

echo "Sync..."

echo "Sync" >> $file
python sync2.py >> $file

echo "Done"
