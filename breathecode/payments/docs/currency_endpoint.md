# Currency Endpoint

## Overview

The currency endpoint allows you to fetch the catalog of available currencies in the system.

## Endpoints

### List All Currencies

```
GET /v1/payments/currency
```

Returns a list of all available currencies.

**Query Parameters:**
- `code` (string, optional): Filter by currency code (exact match)
- `name` (string, optional): Filter by currency name (contains match)
- `limit` (integer, optional): Number of results per page
- `offset` (integer, optional): Number of results to skip
- `sort` (string, optional): Sort field (default: `code`)

**Response:**
```json
[
  {
    "code": "USD",
    "name": "US Dollar",
    "countries": [
      {
        "code": "US",
        "name": "United States"
      }
    ]
  },
  {
    "code": "EUR",
    "name": "Euro",
    "countries": [
      {
        "code": "DE",
        "name": "Germany"
      },
      {
        "code": "FR",
        "name": "France"
      }
    ]
  }
]
```

**Example Requests:**
```bash
# Get all currencies
curl https://api.4geeks.com/v1/payments/currency

# Filter by code
curl https://api.4geeks.com/v1/payments/currency?code=USD

# Filter by name
curl https://api.4geeks.com/v1/payments/currency?name=Dollar

# Paginate results
curl https://api.4geeks.com/v1/payments/currency?limit=10&offset=0

# Sort by name descending
curl https://api.4geeks.com/v1/payments/currency?sort=-name
```

### Get Specific Currency

```
GET /v1/payments/currency/{currency_code}
```

Returns a specific currency by its ISO 4217 code.

**Parameters:**
- `currency_code` (string, required): The ISO 4217 currency code (e.g., USD, EUR, MXN)

**Response:**
```json
{
  "code": "USD",
  "name": "US Dollar",
  "countries": [
    {
      "code": "US",
      "name": "United States"
    }
  ]
}
```

**Error Response (404):**
```json
{
  "detail": "Currency not found",
  "status_code": 404,
  "slug": "currency-not-found"
}
```

**Example Requests:**
```bash
# Get USD currency
curl https://api.4geeks.com/v1/payments/currency/USD

# Works with lowercase too
curl https://api.4geeks.com/v1/payments/currency/usd
```

## Use Cases

1. **Populate currency dropdowns** in payment forms
2. **Validate currency codes** before creating payments
3. **Display available payment currencies** to users
4. **Show currency information** with country associations

## Authentication

This endpoint is **public** (AllowAny) and does not require authentication.

## Notes

- Currency codes are case-insensitive (both `USD` and `usd` work)
- The endpoint returns currencies sorted by code by default
- Countries associated with each currency are included in the response
- The currency catalog is typically managed through the Django admin or management commands

