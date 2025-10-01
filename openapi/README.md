# OpenAPI Specifications

This folder contains OpenAPI specifications and Postman collections for all API features.

## Structure

Each feature has its own folder with:
- `openapi.yaml` - OpenAPI 3.0 specification
- `postman_collection.json` - Postman collection
- `README.md` - Feature-specific documentation

## Available Features

### Subscription Seats
Team-based subscriptions with shared access and auto-recharge.

**Location:** [`subscription-seats/`](subscription-seats/)

**Documentation:**
- [Quick Start Guide](../docs/payments/subscription-seats-guide.md)
- [API Reference](../docs/payments/subscription-seats-api.md)

## How to Use

### OpenAPI Specifications

**View/Edit:**
- [Swagger Editor](https://editor.swagger.io/)
- [Redoc](https://redocly.github.io/redoc/)
- VS Code with OpenAPI extension

**Generate Code:**
```bash
# Generate Python client
openapi-generator-cli generate -i openapi.yaml -g python -o client/

# Generate TypeScript client
openapi-generator-cli generate -i openapi.yaml -g typescript-axios -o client/
```

### Postman Collections

**Import:**
1. Open Postman
2. File → Import
3. Select the `postman_collection.json` file

**Set Environment:**
Create a Postman environment with these variables:
- `base_url` - API base URL
- `user_token_1` - Auth token for user 1
- `user_token_2` - Auth token for user 2

## Contributing

When adding a new feature:

1. Create a new folder: `openapi/[feature-name]/`
2. Add `openapi.yaml` with OpenAPI spec
3. Add `postman_collection.json` with Postman collection
4. Add `README.md` with feature documentation
5. Update this file with a link to your feature

## Tools

### Recommended Tools
- [Postman](https://www.postman.com/) - API testing
- [Swagger Editor](https://editor.swagger.io/) - OpenAPI editing
- [OpenAPI Generator](https://openapi-generator.tech/) - Code generation
- [Redoc](https://redocly.github.io/redoc/) - API documentation

### VS Code Extensions
- OpenAPI (Swagger) Editor
- REST Client
- Thunder Client
