# Subscription Seats - Quick Start Guide

This guide explains how subscription seats work in simple terms.

## What Are Subscription Seats?

Subscription seats allow a **team owner** to share their subscription with other users. Think of it like buying a Netflix family plan - one person pays, but multiple people can use it.

### Key Concepts

- **Subscription Owner**: The person who pays for the subscription
- **Billing Team**: A group of users who share the subscription
- **Seat**: Access granted to one team member
- **Auto-Recharge**: Automatic top-up when balance runs low (both strategies)
- **Consumption Strategy**: How consumables are distributed (PER_TEAM or PER_SEAT)
- **is_team_allowed**: Service flag that determines who gets consumables:
  - `False` = Owner only (personal consumables)
  - `True` = Team/Seats (shared or per-seat consumables)

## Consumption Strategies

### PER_TEAM (Shared Pool) 🤝

Team members share a common pool of consumables.

```
┌─────────────────────────────────────────────┐
│  Subscription Owner (Pays)                  │
└──────────────┬──────────────────────────────┘
               │
               ├─ Owner Consumables (is_team_allowed=False)
               │  ├─ 10 personal mentorship hours
               │  └─ 5 personal event tickets
               │
               └─ Billing Team
                  ├─ Team Consumables (is_team_allowed=True, SHARED)
                  │  ├─ 100 mentorship hours
                  │  └─ 50 event tickets
                  │
                  └─ Team Members
                     ├─ Member A (uses from shared pool)
                     ├─ Member B (uses from shared pool)
                     └─ Member C (uses from shared pool)
```

**Best for:**
- Small teams (3-10 people)
- Flexible usage patterns
- Collaborative environments
- Startups and agencies

**How consumables are allocated:**
- Services with `is_team_allowed=False` → Owner gets personal consumables
- Services with `is_team_allowed=True` → Team gets shared pool

**Example:**
```
Owner: 10 personal hours (is_team_allowed=False)
Team Pool: 100 shared hours (is_team_allowed=True)

Day 1: Team pool has 100 hours
- Member A uses 30 hours → 70 left
- Member B uses 40 hours → 30 left
- Balance low → Auto-recharge adds 50 → 80 left

Owner's 10 personal hours remain untouched
```

### PER_SEAT (Individual Allocation) 👤

Each team member gets their own allocation of consumables.

```
┌─────────────────────────────────────────────┐
│  Subscription Owner (Pays)                  │
└──────────────┬──────────────────────────────┘
               │
               ├─ Owner Consumables (is_team_allowed=False)
               │  ├─ 10 personal mentorship hours
               │  └─ 5 personal event tickets
               │
               └─ Billing Team
                  ├─ Seat 1 (Member A)
                  │  └─ Consumables (is_team_allowed=True, individual)
                  │     ├─ 10 hours
                  │     └─ 5 tickets
                  │
                  ├─ Seat 2 (Member B)
                  │  └─ Consumables (is_team_allowed=True, individual)
                  │     ├─ 10 hours
                  │     └─ 5 tickets
                  │
                  └─ Seat 3 (Member C, 2x multiplier)
                     └─ Consumables (is_team_allowed=True, individual)
                        ├─ 20 hours (2x)
                        └─ 10 tickets (2x)
```

**Best for:**
- Large teams (10+ people)
- Fair distribution required
- Enterprise environments
- Predictable usage per person

**How consumables are allocated:**
- Services with `is_team_allowed=False` → Owner gets personal consumables
- Services with `is_team_allowed=True` → Each seat gets individual consumables

**Example:**
```
Owner: 10 personal hours (is_team_allowed=False)

Member A (1x seat): Gets 10 hours (is_team_allowed=True)
- Uses 8 hours → 2 hours left
- Cannot use other members' hours

Member C (2x seat): Gets 20 hours (is_team_allowed=True, 2x multiplier)
- Uses 15 hours → 5 hours left
- Cannot share with others

Owner's 10 personal hours remain separate
```

## Comparison Table

| Feature | PER_TEAM 🤝 | PER_SEAT 👤 |
|---------|-------------|-------------|
| **Owner Consumables** | `is_team_allowed=False` (personal) | `is_team_allowed=False` (personal) |
| **Team Consumables** | `is_team_allowed=True` (shared pool) | `is_team_allowed=True` (per seat) |
| **Flexibility** | High | Low |
| **Recharge** | Manual or Auto (team) | Manual or Auto (per seat) |
| **Auto-Recharge** | ✅ Team level | ✅ Per seat level |
| **Seat Multiplier** | Not used | Determines allocation |
| **Best For** | Small teams | Large teams |
| **Example** | 5-person startup | 50-person company |

## Basic Workflow

### 1. Create a Subscription

First, the owner creates a subscription with a plan that supports teams.

```bash
POST /v1/payments/checking
{
  "type": "PREVIEW",
  "plans": [1],
  "team_seats": 3
}
```

### 2. Get Billing Team Info

Check the team configuration:

```bash
GET /v2/payments/subscription/123/billing-team
```

**Response**:
```json
{
  "id": 1,
  "subscription": 123,
  "name": "Team 123",
  "seats_limit": 3,
  "seats_count": 2,
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_period_spend": "100.00",
  "current_period_spend": 45.00,
  "currency": "USD"
}
```

### 3. Add Team Members

Add users to the team:

```bash
PUT /v2/payments/subscription/123/billing-team/seat
{
  "add_seats": [
    {
      "email": "member@example.com",
    }
  ]
}
```

### 4. Team Members Use Services

When team members consume services (mentorship, events), it's deducted from the shared team balance.

## Auto-Recharge Feature

Auto-recharge automatically tops up the team balance when it runs low.

### How It Works

1. **Threshold**: When balance falls below $10 (configurable)
2. **Recharge**: Automatically add $20 (configurable)
3. **Limit**: Maximum $100 per month (configurable)

### Configure Auto-Recharge

```bash
PUT /v2/payments/subscription/123/billing-team
{
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_period_spend": "100.00"
}
```

### Example Scenario

```
Day 1:  Balance = $50
Day 5:  Team uses $42 → Balance = $8 (below $10 threshold)
        → Auto-recharge triggers
        → Add $20
        → New balance = $28
Day 10: Team uses $15 → Balance = $13
        (Above threshold, no recharge)
```

## Common Operations

### View All Seats

```bash
GET /v2/payments/subscription/123/billing-team/seat
```

### Remove a Seat

```bash
DELETE /v2/payments/subscription/123/billing-team/seat/456
```

### Replace a Seat

Transfer a seat from one user to another:

```bash
PUT /v2/payments/subscription/123/billing-team/seat
{
  "replace_seats": [
    {
      "from_email": "old@example.com",
      "to_email": "new@example.com"
    }
  ]
}
```

## Important Notes

### Permissions

- Only the **subscription owner** can manage seats
- Team members can only consume services

### Billing

- Owner pays for all team consumption
- Charges appear on owner's invoice
- Monthly spending limits protect from overspending

### Consumption

- Team shares a common balance
- Each member can consume based on their seat multiplier
- Unlimited consumables (how_many = -1) don't trigger auto-recharge

## Troubleshooting

### "Only the owner can manage team"

**Problem**: You're not the subscription owner.

**Solution**: Only the person who created the subscription can add/remove seats.

### "Billing period limit reached"

**Problem**: Team hit the monthly spending limit.

**Solution**: Wait for next billing period or increase `max_period_spend`.

### "No budget available for recharge"

**Problem**: Auto-recharge would exceed monthly limit.

**Solution**: Increase `max_period_spend` or wait for next billing period.

## Next Steps

- [Full API Documentation](subscription-seats-api.md)
- [OpenAPI Specification](../../openapi/subscription-seats/openapi.yaml)
- [Postman Collection](../../openapi/subscription-seats/postman_collection.json)

## Testing & Development

### Import Postman Collection

**File Location:** `openapi/subscription-seats/postman_collection.json`

**Steps:**
1. Open Postman
2. Click "Import" button
3. Select file: `openapi/subscription-seats/postman_collection.json`
4. Set environment variables:
   - `base_url`: `https://breathecode.herokuapp.com` (or your local URL)
   - `user_token_1`: Your authentication token
   - `user_token_2`: Second user token (for testing)

### Use OpenAPI Spec

**File Location:** `openapi/subscription-seats/openapi.yaml`

**View in Swagger Editor:**
1. Go to [editor.swagger.io](https://editor.swagger.io/)
2. File → Import File
3. Select: `openapi/subscription-seats/openapi.yaml`

**Generate API Client:**
```bash
# Python client
openapi-generator-cli generate \
  -i openapi/subscription-seats/openapi.yaml \
  -g python \
  -o client/python/

# TypeScript client
openapi-generator-cli generate \
  -i openapi/subscription-seats/openapi.yaml \
  -g typescript-axios \
  -o client/typescript/
```

## Need Help?

- Check the [API Reference](subscription-seats-api.md) for detailed endpoint documentation
- Review the [OpenAPI spec](../../openapi/subscription-seats/openapi.yaml) for request/response schemas
- Import the [Postman collection](../../openapi/subscription-seats/postman_collection.json) to test endpoints
- See [Payments Overview](index.md) for architecture comparison
