# Subscription Seats - API Specifications

This folder contains the API specifications for the Subscription Seats feature.

## Files

### openapi.yaml
OpenAPI 3.0 specification for all subscription seats endpoints.

**Use this for:**
- Generating API clients
- API documentation tools (Swagger UI, Redoc)
- Contract testing
- Code generation

**View online:**
- Import into [Swagger Editor](https://editor.swagger.io/)
- Use with Redoc or Swagger UI

### postman_collection.json
Postman collection with all endpoints and example requests.

**Use this for:**
- Manual API testing
- Learning the API
- Integration testing
- Debugging

**How to use:**
1. Open Postman
2. Import → Upload Files → Select `postman_collection.json`
3. Set environment variables:
   - `base_url`: API base URL (e.g., `https://breathecode.herokuapp.com`)
   - `user_token_1`: Authentication token for user 1
   - `user_token_2`: Authentication token for user 2

## Quick Links

- **[Quick Start Guide](../../docs/payments/subscription-seats-guide.md)** - Beginner-friendly introduction
- **[API Documentation](../../docs/payments/subscription-seats-api.md)** - Detailed endpoint reference
- **[Payments Index](../../docs/payments/index.md)** - Overview of payments module

## API Endpoints

### Billing Team
- `GET /v2/payments/subscription/{id}/billing-team` - Get team info
- `PUT /v2/payments/subscription/{id}/billing-team` - Update auto-recharge settings

### Seats
- `GET /v2/payments/subscription/{id}/billing-team/seat` - List seats
- `PUT /v2/payments/subscription/{id}/billing-team/seat` - Add/replace seats
- `DELETE /v2/payments/subscription/{id}/billing-team/seat/{seat_id}` - Remove seat

### Consumables
- `POST /v2/payments/consumable/checkout` - Purchase consumables for team

## Testing

### With Postman
1. Import the collection
2. Set up environment variables
3. Run requests in order (follow the collection folders)

### With cURL
See examples in the [API Documentation](../../docs/payments/subscription-seats-api.md)

### With Python
```python
import requests

base_url = "https://breathecode.herokuapp.com"
token = "your_token_here"

# Get billing team
response = requests.get(
    f"{base_url}/v2/payments/subscription/123/billing-team",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
```

## Need Help?

- Read the [Quick Start Guide](../../docs/payments/subscription-seats-guide.md) first
- Check the [API Documentation](../../docs/payments/subscription-seats-api.md) for details
- Review example requests in the Postman collection
