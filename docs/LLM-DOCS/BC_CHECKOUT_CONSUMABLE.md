## Complete Flow to Buy More Consumables

### 1️⃣ **Check Available Services** (Optional but recommended)

Get list of available services you can purchase:

```bash
GET /v1/payments/service?academy={academy_id}
```

**Response:**
```json
[
  {
    "slug": "mentorship-service",
    "title": "Mentorship Service",
    "description": "1-on-1 mentoring sessions",
    "type": "MENTORSHIP_SERVICE",
    ...
  },
  {
    "slug": "event-service",
    "title": "Event Service",
    "description": "Access to workshops and events",
    "type": "EVENT_TYPE_SET",
    ...
  }
]
```

### 2️⃣ **Get Service Pricing** (Optional)

Check pricing for a specific academy and service:

```bash
GET /v1/payments/academy/academyservice/{service_slug}?country_code=US
```

**Headers:**
- `Academy: {academy_id}`

This returns the pricing information for that service at that academy.

### 3️⃣ **Check Current Balance** (Optional)

See your current consumable balance:

```bash
GET /v1/payments/me/service/consumable
```

**Response:**
```json
{
  "mentorship_service_sets": [...],
  "event_type_sets": [...],
  "cohort_sets": [...],
  "voids": [...]
}
```

### 4️⃣ **Verify Payment Method Exists**

Check if you have a card on file:

```bash
GET /v2/payments/card?academy_id={academy_id}
```

**Response if card exists:**
```json
{
  "has_payment_method": true,
  "card_last4": "4242",
  "card_brand": "Visa",
  "card_exp_month": 12,
  "card_exp_year": 2025
}
```

**If no card exists**, add one first:
```bash
POST /v2/payments/card?academy_id={academy_id}
{
  "card_number": "4242424242424242",
  "exp_month": 12,
  "exp_year": 2025,
  "cvc": "123"
}
```

### 5️⃣ **Purchase Consumables** ⭐ Main Endpoint

```bash
POST /v1/payments/consumable/checkout
```

**Request Body:**
```json
{
  "service": "mentorship-service",  // or service ID as integer
  "how_many": 10,                   // number of units to purchase
  "academy": 1,                      // academy ID
  "country_code": "US",             // optional, for pricing
  "is_team_allowed": false
}
```

**Parameters:**
- `service` (required): Service slug (string) or ID (integer)
- `how_many` (required): Number of consumable units to buy (positive number)
- `academy` (required): Academy ID
- `country_code` (optional): For country-specific pricing
- `is_team_allowed` (optional): Whether team consumption is allowed, this is used for buying saas seats

**Response (201 Created):**
```json
{
  "id": 123,
  "amount": 99.99,
  "currency": {
    "code": "USD",
    "name": "US Dollar"
  },
  "paid_at": "2025-10-11T12:34:56Z",
  "status": "FULFILLED",
  "stripe_id": "ch_xxxxx",
  "user": {...},
  "bag": {...}
}
```

### 6️⃣ **Verify Purchase** (Optional)

Check your updated balance:

```bash
GET /v1/payments/me/service/consumable
```

You should see the newly purchased consumables in your balance.

---

## Complete Example Flow

```javascript
// Step 1: Check if payment method exists
const checkCard = await fetch('/v2/payments/card?academy_id=1');
const cardData = await checkCard.json();

if (!cardData.has_payment_method) {
  // User needs to add card first
  alert('Please add a payment method first');
  return;
}

// Step 2: Purchase 10 mentorship sessions
const purchase = await fetch('/v1/payments/consumable/checkout', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Token your-auth-token'
  },
  body: JSON.stringify({
    service: 'mentorship-service',  // or use service ID
    how_many: 10,
    academy: 1,
    country_code: 'US',
    mentorship_service_set: 1  // optional
  })
});

if (purchase.ok) {
  const invoice = await purchase.json();
  console.log('Purchase successful!', invoice);
  console.log(`Charged: ${invoice.amount} ${invoice.currency.code}`);
} else {
  const error = await purchase.json();
  console.error('Purchase failed:', error);
}

// Step 3: Check new balance
const balance = await fetch('/v1/payments/me/service/consumable');
const balanceData = await balance.json();
console.log('New balance:', balanceData);
```

---

## Key Points

✅ **Single endpoint**: `/v1/payments/consumable/checkout` handles the entire purchase
✅ **Uses saved card**: Automatically charges the card you have on file
✅ **Instant delivery**: Consumables are immediately added to your account
✅ **Flexible pricing**: Supports country-specific pricing ratios
✅ **Multiple service types**: Works for mentorships, events, and other services

The system automatically:
- Creates a Bag with the purchase details
- Charges your saved payment method via Stripe
- Creates an Invoice record
- Creates a Consumable with the purchased units
- Logs the activity

No bag/checking flow needed - this is a direct purchase endpoint! 🚀
