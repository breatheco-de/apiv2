# Payments Module

The payments module handles all subscription, billing, and payment-related functionality.

## Features

### Subscription Seats

Team-based subscriptions where one owner can share access with multiple team members.

- **[Quick Start Guide](subscription-seats-guide.md)** - Simple introduction for beginners
- **[API Documentation](subscription-seats-api.md)** - Detailed endpoint reference
- **[OpenAPI Spec](../../openapi/subscription-seats/openapi.yaml)** - Machine-readable API definition
- **[Postman Collection](../../openapi/subscription-seats/postman_collection.json)** - Ready-to-use API tests

### Key Concepts

- **Subscriptions**: Recurring payment plans
- **Billing Teams**: Groups that share subscription access
- **Seats**: Individual team member access
- **Auto-Recharge**: Automatic balance top-up
- **Consumables**: Services that can be consumed (mentorship, events, etc.)
- **Consumption Strategy**: How consumables are distributed (PER_TEAM vs PER_SEAT)
- **is_team_allowed**: Flag that determines consumable allocation:
  - `False`: Consumables go to subscription owner (personal)
  - `True`: Consumables go to team/seats (shared or per-seat)

## Getting Started

1. Read the [Subscription Seats Guide](subscription-seats-guide.md) to understand the basics
2. Review the [API Documentation](subscription-seats-api.md) for implementation details
3. Import the Postman Collection to test endpoints

**File Locations:**
- Postman Collection: `openapi/subscription-seats/postman_collection.json`
- OpenAPI Spec: `openapi/subscription-seats/openapi.yaml`

## Architecture

### PER_TEAM Strategy (Shared Pool)

```
User (Owner)
  └─ Subscription
      ├─ Owner Consumables (is_team_allowed=False)
      │   ├─ 10 personal mentorship hours
      │   └─ 5 personal event tickets
      │
      └─ Billing Team
          ├─ Team Consumables (is_team_allowed=True, SHARED)
          │   ├─ 100 mentorship hours
          │   ├─ 50 event tickets
          │   └─ Auto-recharge enabled
          │
          └─ Seats (Members)
              ├─ Member A (can use team consumables)
              ├─ Member B (can use team consumables)
              └─ Member C (can use team consumables)
```

**How it works:**
- **Owner** gets personal consumables (`is_team_allowed=False`)
- **Team** has a **shared pool** of consumables (`is_team_allowed=True`)
- Any team member can consume from the shared pool
- When pool runs low, auto-recharge tops it up
- Owner pays for all consumption

**Service Item Flag:**
- `is_team_allowed=False` → Consumables issued to **owner only**
- `is_team_allowed=True` → Consumables issued to **team pool**

**Example:**
```
Team has 100 mentorship hours
- Member A uses 30 hours → 70 hours left
- Member B uses 40 hours → 30 hours left
- Member C uses 20 hours → 10 hours left
- Auto-recharge adds 50 hours → 60 hours left
```

### PER_SEAT Strategy (Individual Allocation)

```
User (Owner)
  └─ Subscription
      ├─ Owner Consumables (is_team_allowed=False)
      │   ├─ 10 personal mentorship hours
      │   └─ 5 personal event tickets
      │
      └─ Billing Team
          ├─ Seat 1 (Member A)
          │   └─ Consumables (is_team_allowed=True, individual)
          │       ├─ 10 mentorship hours
          │       └─ 5 event tickets
          │
          ├─ Seat 2 (Member B)
          │   └─ Consumables (is_team_allowed=True, individual)
          │       ├─ 10 mentorship hours
          │       └─ 5 event tickets
          │
          └─ Seat 3 (Member C)
              └─ Consumables (is_team_allowed=True, individual)
                  ├─ 20 mentorship hours (2x multiplier)
                  └─ 10 event tickets (2x multiplier)
```

**How it works:**
- **Owner** gets personal consumables (`is_team_allowed=False`)
- Each **seat** has **individual allocation** (`is_team_allowed=True`)
- Members can only use their own consumables
- Seat multiplier determines allocation (2x = double)
- Owner pays for all seats

**Service Item Flag:**
- `is_team_allowed=False` → Consumables issued to **owner only**
- `is_team_allowed=True` → Consumables issued to **each seat individually**

**Example:**
```
Member A (1x seat):
- Gets 10 mentorship hours
- Uses 8 hours → 2 hours left
- Cannot use Member B's hours

Member C (2x seat):
- Gets 20 mentorship hours (2x multiplier)
- Uses 15 hours → 5 hours left
- Cannot share with others
```

## Comparison

| Feature | PER_TEAM | PER_SEAT |
|---------|----------|----------|
| **Owner Consumables** | `is_team_allowed=False` (personal) | `is_team_allowed=False` (personal) |
| **Team Consumables** | `is_team_allowed=True` (shared pool) | `is_team_allowed=True` (per seat) |
| **Flexibility** | High (anyone can use) | Low (fixed per member) |
| **Recharge** | Manual or Auto (team level) | Manual or Auto (per seat) |
| **Auto-Recharge** | ✅ Supported | ✅ Supported (per seat) |
| **Seat Multiplier** | Not used | Determines allocation |
| **Use Case** | Small teams, flexible usage | Large teams, fair distribution |
| **Example** | Startup with 3 devs | Enterprise with 50 employees |

## Related Modules

- **Provisioning**: Manages consumable allocation
- **Monitoring**: Tracks usage and spending
- **Notify**: Sends payment notifications
