#!/bin/bash

# Test script for catalog endpoints
# Run this while your dev server is running

BASE_URL="http://localhost:8000"

echo "Testing Catalog Endpoints..."
echo "=============================="
echo ""

# Test timezones (existing endpoint that should work)
echo "1. Testing /v1/admissions/catalog/timezones"
curl -s -o /dev/null -w "Status: %{http_code}\n" "${BASE_URL}/v1/admissions/catalog/timezones"
echo ""

# Test countries
echo "2. Testing /v1/admissions/catalog/countries"
curl -s -o /dev/null -w "Status: %{http_code}\n" "${BASE_URL}/v1/admissions/catalog/countries"
echo ""

# Test cities
echo "3. Testing /v1/admissions/catalog/cities"  
curl -s -o /dev/null -w "Status: %{http_code}\n" "${BASE_URL}/v1/admissions/catalog/cities"
echo ""

echo "=============================="
echo "Expected: All should return 200"
echo ""
echo "If you see 401, restart your dev server:"
echo "  poetry run python manage.py runserver"

