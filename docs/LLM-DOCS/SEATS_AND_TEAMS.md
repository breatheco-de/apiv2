# Seats and Teams - Complete Guide

This document provides comprehensive guidance on seat-based consumption, team management, and how organizations can share subscription access across multiple team members in the BreatheCode platform.

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [How Seat-Based Consumption Works](#how-seat-based-consumption-works)
4. [Creating a Billing Team](#creating-a-billing-team)
5. [Managing Team Seats](#managing-team-seats)
6. [Team Settings & Auto-Recharge](#team-settings--auto-recharge)
7. [Consumption Strategies](#consumption-strategies)
8. [Consumables and Seats](#consumables-and-seats)
9. [Inviting Team Members](#inviting-team-members)
10. [Removing Team Members](#removing-team-members)
11. [Seat Limits and Scaling](#seat-limits-and-scaling)
12. [Billing and Charges](#billing-and-charges)
13. [API Reference](#api-reference)
14. [Complete Workflows](#complete-workflows)

---

## Overview

**Seat-based consumption** allows subscription owners to share their plan access with team members. Instead of each person purchasing their own subscription, a company can buy a team subscription and assign "seats" to employees or students.

### Key Benefits

- **Cost Efficiency**: Centralized billing for entire teams
- **Access Control**: Owner manages who has access
- **Flexible Scaling**: Add or remove seats as needed
- **Shared Resources**: Team members consume from a shared pool
- **Usage Tracking**: Monitor consumption per seat

### Base URL

```
Production: https://breathecode.herokuapp.com
Development: http://localhost:8000
```

---

## Core Concepts

### 1. Subscription

The base subscription purchased by an owner (individual or organization).

```json
{
  "id": 123,
  "user": 456,
  "status": "ACTIVE",
  "has_billing_team": true
}
```

### 2. Billing Team

A team entity attached to a subscription. Each subscription can have ONE billing team.

```json
{
  "id": 789,
  "subscription": 123,
  "name": "Team 123",
  "seats_limit": 10,
  "additional_seats": 9,
  "seats_count": 7,
  "consumption_strategy": "PER_SEAT"
}
```

**Key Fields:**
- `seats_limit`: Total seats available (including owner)
- `additional_seats`: Paid seats beyond the owner's seat
- `seats_count`: Currently occupied seats
- `consumption_strategy`: How consumption is tracked

### 3. Subscription Seat

A seat represents one team member's access to the subscription.

```json
{
  "id": 101,
  "billing_team": 789,
  "user": 456,
  "email": "member@company.com",
  "is_active": true
}
```

**Seat States:**
- **Active with User**: Seat occupied by a registered user
- **Active without User**: Seat reserved for an email (pending invite)
- **Inactive**: Seat removed/freed

### 4. Consumable

Resources (credits, hours, etc.) that can be consumed by team members.

```json
{
  "id": 202,
  "subscription": 123,
  "subscription_billing_team": 789,
  "subscription_seat": 101,
  "user": 456,
  "service_item": {...},
  "how_many": 100,
  "balance": 75
}
```

---

## How Seat-Based Consumption Works

### Basic Flow

```
1. Owner purchases subscription
   ↓
2. Checkout creates billing team (if requesting seats)
   ↓
3. Owner gets first seat automatically (free)
   ↓
4. Owner invites team members (each consumes 1 seat)
   ↓
5. Team members consume resources from shared pool
   ↓
6. Consumption tracked per seat or per team
```

### Consumption Strategies

There are TWO consumption strategies:

#### 1. PER_SEAT (Default)

Each seat member has their own allocated resources.

**Example:**
- Plan: 100 hours per seat
- Team: 5 seats
- Result: Each member gets 100 hours (500 hours total)

```json
{
  "consumption_strategy": "PER_SEAT",
  "seats_count": 5
}
```

**Consumables:**
- Each seat gets individual consumables
- When seat is removed, their consumables are freed
- Tracked by `subscription_seat` foreign key

#### 2. PER_TEAM

Entire team shares from a single resource pool.

**Example:**
- Plan: 500 hours total
- Team: 5 seats
- Result: All 5 members share 500 hours

```json
{
  "consumption_strategy": "PER_TEAM",
  "seats_count": 5
}
```

**Consumables:**
- One shared consumable for the team
- Resources deplete from common pool
- Tracked by `subscription_billing_team` only

---

## Creating a Billing Team

Billing teams are typically created automatically during checkout when the plan supports seats.

### Automatic Creation (During Checkout)

**Endpoint:** `POST /v1/payments/consumable/checkout`

**Request:**

```json
{
  "plan": 1,
  "additional_seats": 9,
  "currency": "USD"
}
```

**What Happens:**

1. Creates subscription
2. Creates billing team with 10 seats (9 additional + 1 owner)
3. Assigns owner as first seat
4. Creates seat-specific consumables
5. Returns checkout success

**Response:**

```json
{
  "status": "fulfilled",
  "subscription": {
    "id": 123,
    "has_billing_team": true,
    "status": "ACTIVE"
  },
  "billing_team": {
    "id": 789,
    "seats_limit": 10,
    "seats_count": 1
  }
}
```

### Example: Purchase Team Plan

```javascript
const purchaseTeamPlan = async (planId, seatCount) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    'https://breathecode.herokuapp.com/v1/payments/consumable/checkout',
    {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        plan: planId,
        additional_seats: seatCount - 1,  // -1 because owner gets first seat
        currency: 'USD'
      })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Checkout failed');
  }

  return await response.json();
};

// Purchase plan with 10 total seats
const result = await purchaseTeamPlan(1, 10);
console.log(`Team created with ${result.billing_team.seats_limit} seats`);
```

---

## Managing Team Seats

### View Billing Team

**Endpoint:** `GET /v1/payments/subscription/{subscription_id}/billing-team`

**Purpose:** Get team details, seat count, and spending info.

**Response:**

```json
{
  "id": 789,
  "subscription": 123,
  "name": "Team 123",
  "seats_limit": 10,
  "additional_seats": 9,
  "seats_count": 7,
  "seats_log": [],
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "100.00",
  "max_period_spend": "1000.00",
  "current_period_spend": 250.50,
  "period_start": "2024-02-01T00:00:00",
  "period_end": "2024-02-29T23:59:59",
  "currency": "USD"
}
```

**Example:**

```javascript
const getBillingTeam = async (subscriptionId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/billing-team`,
    {
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );

  return await response.json();
};
```

### List All Seats

**Endpoint:** `GET /v1/payments/subscription/{subscription_id}/seat`

**Purpose:** Get all seats in the team.

**Response:**

```json
[
  {
    "id": 101,
    "email": "owner@company.com",
    "user": 456,
    "is_active": true,
    "seat_log": []
  },
  {
    "id": 102,
    "email": "member1@company.com",
    "user": 457,
    "is_active": true,
    "seat_log": []
  },
  {
    "id": 103,
    "email": "pending@company.com",
    "user": null,
    "is_active": true,
    "seat_log": []
  }
]
```

**Example:**

```javascript
const listSeats = async (subscriptionId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
    {
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );

  return await response.json();
};
```

### Get Single Seat

**Endpoint:** `GET /v1/payments/subscription/{subscription_id}/seat/{seat_id}`

**Purpose:** Get details for one specific seat.

---

## Managing Team Seats

### Add New Seats

**Endpoint:** `PUT /v1/payments/subscription/{subscription_id}/seat`

**Purpose:** Add one or more seats to the team.

**Request Body:**

```json
{
  "add_seats": [
    {
      "email": "newmember@company.com",
      "user": null
    },
    {
      "email": "anothermember@company.com",
      "user": 789
    }
  ]
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | ✅ Yes | Email address (will be normalized to lowercase) |
| `user` | integer | ❌ No | User ID if already registered, null for invite |

**Response (207 Multi-Status):**

```json
{
  "data": [
    {
      "id": 104,
      "email": "newmember@company.com",
      "user": null,
      "is_active": true,
      "seat_log": []
    },
    {
      "id": 105,
      "email": "anothermember@company.com",
      "user": 789,
      "is_active": true,
      "seat_log": []
    }
  ],
  "errors": []
}
```

**Example:**

```javascript
const addSeats = async (subscriptionId, seats) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        add_seats: seats
      })
    }
  );

  return await response.json();
};

// Add two new members
const result = await addSeats(123, [
  { email: 'alice@company.com', user: null },
  { email: 'bob@company.com', user: 456 }
]);

console.log(`Added ${result.data.length} seats`);
if (result.errors.length > 0) {
  console.error('Some seats failed:', result.errors);
}
```

### Replace Seats

**Endpoint:** `PUT /v1/payments/subscription/{subscription_id}/seat`

**Purpose:** Replace one seat with another (useful when someone leaves the team).

**Request Body:**

```json
{
  "replace_seats": [
    {
      "from_email": "old@company.com",
      "to_email": "new@company.com",
      "to_user": null
    }
  ]
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_email` | string | ✅ Yes | Current seat email to replace |
| `to_email` | string | ✅ Yes | New seat email |
| `to_user` | integer | ❌ No | New user ID if registered |

**What Happens:**
1. Finds existing seat by `from_email`
2. Updates seat to `to_email` and `to_user`
3. Sends invitation if `to_user` is null
4. Transfers any existing consumables

**Example:**

```javascript
const replaceSeat = async (subscriptionId, fromEmail, toEmail, toUser = null) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        replace_seats: [
          {
            from_email: fromEmail,
            to_email: toEmail,
            to_user: toUser
          }
        ]
      })
    }
  );

  return await response.json();
};

// Replace departed employee with new hire
await replaceSeat(123, 'john@company.com', 'jane@company.com');
```

### Remove Seat

**Endpoint:** `DELETE /v1/payments/subscription/{subscription_id}/seat/{seat_id}`

**Purpose:** Deactivate a seat and free resources.

**What Happens:**
1. Marks seat as `is_active=false`
2. Removes user association
3. Clears user from associated consumables
4. Seat slot becomes available for reuse

**Example:**

```javascript
const removeSeat = async (subscriptionId, seatId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat/${seatId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );

  if (response.status === 204) {
    console.log('Seat removed successfully');
  }
};

// Remove a team member
await removeSeat(123, 105);
```

**Important Notes:**
- Only the subscription owner can manage seats
- Removing a seat doesn't delete it, it deactivates it
- The freed slot can be reassigned to someone else
- Owner's seat (first seat) cannot be removed

---

## Plan Financing Seats

Plan financings now support their own team and seat management flow, separated from subscriptions.

- **Team Endpoint:** `GET /v2/payments/plan-financing/{plan_financing_id}/team`
- **Seat Endpoint:** `GET|PUT|DELETE /v2/payments/plan-financing/{plan_financing_id}/team/seat`
- Only the financing owner can view or modify seats.
- Seat limits mirror the purchased seats in the financing (owner seat + additional seats).
- Seat operations reuse the same payload shape as subscription seats (`add_seats`, `replace_seats`).
- Auto-recharge, when enabled on the financing, follows the same thresholds and spend limits as subscriptions.
- When consumption strategy is `PER_SEAT`, consumables are tied to each financing seat.
- When consumption strategy is `PER_TEAM`, consumables are shared across the financing team.

> Note: Invitations for unregistered users are not yet available for plan financings; seats created without a user stay pending until manually reassigned.

## Team Settings & Auto-Recharge

Billing teams can be configured to automatically recharge when running low on credits.

### Update Team Settings

**Endpoint:** `PUT /v1/payments/subscription/{subscription_id}/billing-team`

**Purpose:** Configure auto-recharge and spending limits.

**Request Body:**

```json
{
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "100.00",
  "max_period_spend": "1000.00"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `auto_recharge_enabled` | boolean | ❌ No | Enable automatic recharging |
| `recharge_threshold_amount` | string | ❌ No | Balance threshold to trigger recharge |
| `recharge_amount` | string | ❌ No | Amount to recharge when triggered |
| `max_period_spend` | string | ❌ No | Maximum spending per billing period |

**How Auto-Recharge Works:**

1. Team consumes resources (credits decrease)
2. When balance drops below `recharge_threshold_amount`
3. System automatically purchases `recharge_amount` more credits
4. Continues until `max_period_spend` limit reached

**Example:**

```javascript
const updateTeamSettings = async (subscriptionId, settings) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/billing-team`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(settings)
    }
  );

  return await response.json();
};

// Configure auto-recharge
await updateTeamSettings(123, {
  auto_recharge_enabled: true,
  recharge_threshold_amount: '20.00',  // Recharge when balance < $20
  recharge_amount: '100.00',            // Add $100 each time
  max_period_spend: '500.00'            // Don't exceed $500/month
});
```

### Spending Monitoring

The billing team tracks spending per period:

```json
{
  "current_period_spend": 250.50,
  "max_period_spend": "500.00",
  "period_start": "2024-02-01T00:00:00",
  "period_end": "2024-02-29T23:59:59"
}
```

**Use this to:**
- Display budget remaining
- Alert when approaching limit
- Generate spending reports

---

## Consumption Strategies

Plans can support different consumption models.

### Plan Consumption Strategy

When creating a plan, specify the strategy:

```json
{
  "slug": "team-plan",
  "title": "Team Plan",
  "consumption_strategy": "PER_SEAT",
  "seat_service_price": 50.00
}
```

**Options:**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `PER_SEAT` | Each seat gets individual resources | Training programs with per-student allocation |
| `PER_TEAM` | Team shares pooled resources | Development teams sharing computing credits |
| `BOTH` | Owner chooses at checkout | Flexible plans |

### Consumable Allocation

#### PER_SEAT Strategy

```javascript
// When seat is added, create individual consumables
{
  "subscription": 123,
  "subscription_billing_team": 789,
  "subscription_seat": 101,
  "user": 456,
  "how_many": 100  // This seat's allocation
}
```

**Consumption:**
- User 456 consumes from their 100 units
- Other seats have their own allocations
- Independent tracking per user

#### PER_TEAM Strategy

```javascript
// All seats share one consumable
{
  "subscription": 123,
  "subscription_billing_team": 789,
  "subscription_seat": null,
  "user": null,
  "how_many": 500  // Shared pool
}
```

**Consumption:**
- Any team member consumes from 500 units
- No per-user tracking
- Team-wide limit

---

## Consumables and Seats

### View Team Consumables

Consumables represent the actual resources (credits, hours, etc.) available to the team.

**Query by Subscription:**

```javascript
const getTeamConsumables = async (subscriptionId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/consumable?subscription=${subscriptionId}`,
    {
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );

  return await response.json();
};
```

**Response:**

```json
[
  {
    "id": 201,
    "service_item": {
      "service": "mentorship",
      "how_many": 10
    },
    "subscription": 123,
    "subscription_billing_team": 789,
    "subscription_seat": 101,
    "user": 456,
    "how_many": 10,
    "balance": 7,
    "valid_until": "2024-12-31T23:59:59Z"
  },
  {
    "id": 202,
    "service_item": {
      "service": "mentorship",
      "how_many": 10
    },
    "subscription": 123,
    "subscription_billing_team": 789,
    "subscription_seat": 102,
    "user": 457,
    "how_many": 10,
    "balance": 9
  }
]
```

### View Seat-Specific Consumables

```javascript
const getSeatConsumables = async (subscriptionId, seatId) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/consumable?subscription=${subscriptionId}&seat=${seatId}`,
    {
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );

  return await response.json();
};
```

---

## Inviting Team Members

When you add a seat without a `user` ID, an invitation is automatically sent.

### Invitation Flow

```
1. Owner adds seat with email only
   ↓
2. System creates SubscriptionSeat (user=null)
   ↓
3. System creates UserInvite
   ↓
4. Invitation email sent to member
   ↓
5. Member clicks link and registers
   ↓
6. SubscriptionSeat updated with user ID
   ↓
7. Member gains access to team resources
```

### Add Seat with Invitation

```javascript
const inviteTeamMember = async (subscriptionId, email) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        add_seats: [
          {
            email: email,
            user: null  // null triggers invitation
          }
        ]
      })
    }
  );

  return await response.json();
};

// Invite a new member
const result = await inviteTeamMember(123, 'newbie@company.com');
console.log('Invitation sent!');
```

### Check Pending Invitations

```javascript
// List seats to see which don't have users yet
const seats = await listSeats(123);
const pending = seats.filter(seat => seat.user === null && seat.is_active);

console.log(`${pending.length} pending invitations:`);
pending.forEach(seat => {
  console.log(`- ${seat.email} (Seat ID: ${seat.id})`);
});
```

---

## Removing Team Members

### Deactivate Seat

To remove someone from the team:

```javascript
const removeTeamMember = async (subscriptionId, seatId) => {
  const token = localStorage.getItem('authToken');
  
  await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat/${seatId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Token ${token}`
      }
    }
  );
};
```

**What Happens:**
- Seat marked `is_active=false`
- User loses access immediately
- Consumables remain but `user` field cleared
- Seat count decreases by 1
- Slot available for new member

### Reactivate Slot

The deactivated seat can be reassigned:

```javascript
// Add new member (will reuse available slots)
await addSeats(123, [
  { email: 'replacement@company.com', user: null }
]);
```

---

## Seat Limits and Scaling

### Check Available Seats

```javascript
const getAvailableSeats = async (subscriptionId) => {
  const team = await getBillingTeam(subscriptionId);
  const available = team.seats_limit - team.seats_count;
  
  console.log(`Available seats: ${available} of ${team.seats_limit}`);
  return available;
};
```

### Scale Up (Buy More Seats)

To increase seat limit, purchase additional seats through checkout:

```javascript
const addMoreSeats = async (subscriptionId, additionalSeats) => {
  const token = localStorage.getItem('authToken');
  
  // This would typically be handled through the checkout flow
  // Contact support or use upgrade endpoint
  
  console.log(`Request ${additionalSeats} more seats for subscription ${subscriptionId}`);
};
```

**Note:** Currently, seat limit changes may require contacting support or going through a separate checkout flow.

### Seat Limit Validation

When adding seats, the system validates against the limit:

```javascript
try {
  await addSeats(123, [
    { email: 'user1@company.com' },
    { email: 'user2@company.com' },
    { email: 'user3@company.com' }
  ]);
} catch (error) {
  if (error.message.includes('seat limit')) {
    console.error('Cannot add seats: limit reached');
    // Prompt to purchase more seats
  }
}
```

---

## Billing and Charges

### How Team Billing Works

1. **Initial Purchase:**
   - Owner pays for subscription
   - Includes base fee + (seat price × additional seats)

2. **Seat Charges:**
   - Each additional seat beyond owner costs extra
   - Charged monthly based on plan's `seat_service_price`

3. **Consumption Charges:**
   - Team members consume resources (credits, hours)
   - Charges based on consumption strategy
   - PER_SEAT: Each seat billed individually
   - PER_TEAM: Team billed for total usage

4. **Auto-Recharge:**
   - When enabled, automatically purchases more credits
   - Charged to subscription owner's payment method
   - Subject to `max_period_spend` limit

### View Current Period Spending

```javascript
const getTeamSpending = async (subscriptionId) => {
  const team = await getBillingTeam(subscriptionId);
  
  console.log('Current Period:', {
    start: team.period_start,
    end: team.period_end,
    spent: team.current_period_spend,
    limit: team.max_period_spend,
    remaining: parseFloat(team.max_period_spend) - team.current_period_spend
  });
  
  return team;
};
```

---

## API Reference

### Complete Endpoint List

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/v1/payments/consumable/checkout` | POST | Purchase team plan | ✅ Required |
| `/v1/payments/subscription/{id}/billing-team` | GET | Get billing team info | ✅ Owner only |
| `/v1/payments/subscription/{id}/billing-team` | PUT | Update team settings | ✅ Owner only |
| `/v1/payments/subscription/{id}/seat` | GET | List all seats | ✅ Owner only |
| `/v1/payments/subscription/{id}/seat/{seat_id}` | GET | Get single seat | ✅ Owner only |
| `/v1/payments/subscription/{id}/seat` | PUT | Add/replace seats | ✅ Owner only |
| `/v1/payments/subscription/{id}/seat/{seat_id}` | DELETE | Remove seat | ✅ Owner only |
| `/v1/payments/consumable` | GET | List consumables | ✅ Required |

### Query Parameters

**List Consumables:**

| Parameter | Example | Description |
|-----------|---------|-------------|
| `subscription` | `?subscription=123` | Filter by subscription |
| `user` | `?user=456` | Filter by user |
| `service` | `?service=mentorship` | Filter by service |

---

## Complete Workflows

### Workflow 1: Create Team and Invite Members

```javascript
// Step 1: Purchase team plan with 5 seats
const checkout = await fetch(
  'https://breathecode.herokuapp.com/v1/payments/consumable/checkout',
  {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      plan: 1,
      additional_seats: 4,  // 4 + 1 owner = 5 total
      currency: 'USD'
    })
  }
).then(r => r.json());

const subscriptionId = checkout.subscription.id;
console.log(`Created subscription ${subscriptionId} with 5 seats`);

// Step 2: Invite team members
const inviteResult = await fetch(
  `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
  {
    method: 'PUT',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      add_seats: [
        { email: 'alice@company.com', user: null },
        { email: 'bob@company.com', user: null },
        { email: 'carol@company.com', user: null },
        { email: 'dave@company.com', user: null }
      ]
    })
  }
).then(r => r.json());

console.log(`Invited ${inviteResult.data.length} members`);

// Step 3: Configure auto-recharge
await fetch(
  `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/billing-team`,
  {
    method: 'PUT',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      auto_recharge_enabled: true,
      recharge_threshold_amount: '50.00',
      recharge_amount: '200.00',
      max_period_spend: '1000.00'
    })
  }
);

console.log('✅ Team created and configured!');
```

### Workflow 2: Monitor Team Usage

```javascript
// Get team overview
const team = await fetch(
  `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/billing-team`,
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());

console.log('Team Overview:');
console.log(`- Seats: ${team.seats_count}/${team.seats_limit}`);
console.log(`- Period spend: $${team.current_period_spend}/$${team.max_period_spend}`);
console.log(`- Auto-recharge: ${team.auto_recharge_enabled ? 'ON' : 'OFF'}`);

// Get all seats
const seats = await fetch(
  `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());

console.log('\nSeats:');
seats.forEach(seat => {
  const status = seat.user ? 'Active' : 'Pending';
  console.log(`- ${seat.email}: ${status}`);
});

// Get consumables
const consumables = await fetch(
  `https://breathecode.herokuapp.com/v1/payments/consumable?subscription=${subscriptionId}`,
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());

console.log('\nConsumables:');
consumables.forEach(c => {
  const percent = ((c.balance / c.how_many) * 100).toFixed(0);
  console.log(`- ${c.service_item.service}: ${c.balance}/${c.how_many} (${percent}%)`);
});
```

### Workflow 3: Replace Departing Member

```javascript
// Step 1: Find the seat to replace
const seats = await fetch(
  `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
  { headers: { 'Authorization': `Token ${token}` } }
).then(r => r.json());

const departingSeat = seats.find(s => s.email === 'leaving@company.com');

if (departingSeat) {
  // Step 2: Replace with new member
  await fetch(
    `https://breathecode.herokuapp.com/v1/payments/subscription/${subscriptionId}/seat`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        replace_seats: [
          {
            from_email: 'leaving@company.com',
            to_email: 'newmember@company.com',
            to_user: null  // Will send invitation
          }
        ]
      })
    }
  );
  
  console.log('✅ Member replaced successfully');
}
```

---

## Best Practices

### 1. Always Check Seat Availability

```javascript
const canAddSeats = async (subscriptionId, count) => {
  const team = await getBillingTeam(subscriptionId);
  const available = team.seats_limit - team.seats_count;
  
  if (available < count) {
    throw new Error(`Only ${available} seats available, need ${count}`);
  }
  
  return true;
};

// Before adding
await canAddSeats(123, 3);
await addSeats(123, [...]);
```

### 2. Handle Partial Failures

The seat endpoint returns 207 Multi-Status:

```javascript
const result = await addSeats(123, seats);

if (result.errors.length > 0) {
  console.warn('Some seats failed:');
  result.errors.forEach(err => {
    console.warn(`- ${err.message}`);
  });
}

if (result.data.length > 0) {
  console.log(`Successfully added ${result.data.length} seats`);
}
```

### 3. Monitor Spending Limits

```javascript
const checkSpendingLimit = async (subscriptionId) => {
  const team = await getBillingTeam(subscriptionId);
  const remaining = parseFloat(team.max_period_spend) - team.current_period_spend;
  const percentUsed = (team.current_period_spend / parseFloat(team.max_period_spend)) * 100;
  
  if (percentUsed > 80) {
    console.warn(`⚠️ ${percentUsed.toFixed(0)}% of budget used`);
  }
  
  return remaining;
};
```

### 4. Use Replace Instead of Remove+Add

When swapping members, use replace to maintain continuity:

```javascript
// ❌ Bad: Remove then add (loses history)
await removeSeat(123, oldSeatId);
await addSeats(123, [{ email: 'new@company.com' }]);

// ✅ Good: Replace (maintains seat slot)
await replaceSeat(123, 'old@company.com', 'new@company.com');
```

---

## Troubleshooting

### Common Issues

#### Issue: "Only the owner can manage team members"

**Cause:** Non-owner trying to manage seats.

**Solution:** Only the subscription owner can add/remove team members.

#### Issue: "Seat limit exceeded"

**Cause:** Trying to add more seats than available.

**Solution:** Check available seats or purchase more:

```javascript
const team = await getBillingTeam(subscriptionId);
console.log(`Available: ${team.seats_limit - team.seats_count}`);
```

#### Issue: "Seat not found"

**Cause:** Seat ID doesn't exist or is inactive.

**Solution:** List all seats to verify:

```javascript
const seats = await listSeats(subscriptionId);
const activeSeat = seats.find(s => s.id === seatId && s.is_active);
```

#### Issue: "Team not found"

**Cause:** Subscription doesn't have a billing team.

**Solution:** Billing team is created during checkout. Verify:

```javascript
const subscription = await getSubscription(subscriptionId);
if (!subscription.has_billing_team) {
  console.error('This subscription does not support teams');
}
```

---

## Related Documentation

- [ACADEMY_PLANS.md](./ACADEMY_PLANS.md) - Plan creation and pricing
- [BC_CHECKOUT_CONSUMABLE.md](./BC_CHECKOUT_CONSUMABLE.md) - Checkout process
- [AUTHENTICATION.md](./AUTHENTICATION.md) - API authentication

---

## Support

For questions or issues with seats and teams:
- Verify you are the subscription owner
- Check seat limits before adding members
- Monitor spending to avoid exceeding limits
- Contact support for seat limit increases

**Last Updated:** October 2024

