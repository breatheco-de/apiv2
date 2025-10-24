## 📋 User Invoice History Endpoint

### Get All Invoices (History)

```bash
GET /v1/payments/me/invoice
```

**Query Parameters** (all optional):
- `status` - Filter by status (comma-separated): `FULFILLED`, `REJECTED`, `PENDING`, `REFUNDED`, `DISPUTED_AS_FRAUD`
- `limit` - Number of results per page
- `offset` - Pagination offset
- `sort` - Sort field (default: `-id` - newest first)

**Example Requests:**

```bash
# Get all invoices (paginated, newest first)
GET /v1/payments/me/invoice

# Get only fulfilled (paid) invoices
GET /v1/payments/me/invoice?status=FULFILLED

# Get fulfilled and refunded invoices
GET /v1/payments/me/invoice?status=FULFILLED,REFUNDED

# Get first 10 invoices
GET /v1/payments/me/invoice?limit=10&offset=0

# Sort by oldest first
GET /v1/payments/me/invoice?sort=id
```

**Response Structure:**
```json
{
  "count": 25,
  "first": null,
  "last": null,
  "next": "http://api.example.com/v1/payments/me/invoice?limit=20&offset=20",
  "previous": null,
  "results": [
    {
      "id": 123,
      "amount": 99.99,
      "currency": {
        "code": "USD",
        "name": "US Dollar"
      },
      "paid_at": "2025-10-11T12:34:56Z",
      "refunded_at": null,
      "status": "FULFILLED",
      "stripe_id": "ch_xxxxxxxxxxxxx",
      "refund_stripe_id": null,
      "amount_refunded": 0.0,
      "externally_managed": false,
      "created_at": "2025-10-11T12:34:56Z",
      "updated_at": "2025-10-11T12:34:56Z"
    },
    {
      "id": 122,
      "amount": 49.99,
      "currency": {
        "code": "USD",
        "name": "US Dollar"
      },
      "paid_at": "2025-09-11T10:20:30Z",
      "refunded_at": null,
      "status": "FULFILLED",
      "stripe_id": "ch_yyyyyyyyyyyyy",
      "refund_stripe_id": null,
      "amount_refunded": 0.0,
      "externally_managed": false,
      "created_at": "2025-09-11T10:20:30Z",
      "updated_at": "2025-09-11T10:20:30Z"
    }
  ]
}
```

---

### Get Single Invoice Details

```bash
GET /v1/payments/me/invoice/{invoice_id}
```

**Example:**
```bash
GET /v1/payments/me/invoice/123
```

**Response** (more detailed):
```json
{
  "id": 123,
  "amount": 99.99,
  "currency": {
    "code": "USD",
    "name": "US Dollar",
    "decimals": 2
  },
  "paid_at": "2025-10-11T12:34:56Z",
  "refunded_at": null,
  "status": "FULFILLED",
  "stripe_id": "ch_xxxxxxxxxxxxx",
  "refund_stripe_id": null,
  "amount_refunded": 0.0,
  "externally_managed": false,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "academy": {
    "id": 1,
    "name": "4Geeks Academy"
  },
  "bag": {
    "id": 456,
    "type": "BAG",
    "status": "PAID",
    "was_delivered": true,
    "chosen_period": "MONTH",
    "is_recurrent": true
  },
  "created_at": "2025-10-11T12:34:56Z",
  "updated_at": "2025-10-11T12:34:56Z"
}
```

---

## Invoice Statuses

| Status | Description |
|--------|-------------|
| `FULFILLED` | Payment completed successfully ✅ |
| `PENDING` | Payment processing or awaiting confirmation ⏳ |
| `REJECTED` | Payment was rejected ❌ |
| `REFUNDED` | Payment was refunded 💰 |
| `DISPUTED_AS_FRAUD` | Payment disputed as fraudulent ⚠️ |

---

## Complete Example Usage

```javascript
// Get invoice history
async function getInvoiceHistory() {
  const response = await fetch('/v1/payments/me/invoice?limit=20', {
    headers: {
      'Authorization': 'Token your-auth-token'
    }
  });

  const data = await response.json();

  console.log(`Total invoices: ${data.count}`);
  console.log('Recent invoices:', data.results);

  // Show invoice details
  data.results.forEach(invoice => {
    console.log(`
      Invoice #${invoice.id}
      Amount: ${invoice.currency.code} ${invoice.amount}
      Date: ${invoice.paid_at}
      Status: ${invoice.status}
      ${invoice.stripe_id ? `Stripe: ${invoice.stripe_id}` : ''}
    `);
  });

  return data;
}

// Get specific invoice
async function getInvoiceDetails(invoiceId) {
  const response = await fetch(`/v1/payments/me/invoice/${invoiceId}`, {
    headers: {
      'Authorization': 'Token your-auth-token'
    }
  });

  const invoice = await response.json();
  console.log('Invoice details:', invoice);
  return invoice;
}

// Get only paid invoices
async function getPaidInvoices() {
  const response = await fetch('/v1/payments/me/invoice?status=FULFILLED', {
    headers: {
      'Authorization': 'Token your-auth-token'
    }
  });

  return await response.json();
}
```

---

## Bonus: Academy Staff View

If you have academy staff permissions, you can also view invoices for your academy:

```bash
GET /v1/payments/academy/invoice
Headers: Academy: {academy_id}
```

Requires `read_invoice` capability.

---

## Summary

✅ **Yes, there's a full invoice history endpoint**: `/v1/payments/me/invoice`  
✅ **Supports filtering** by status  
✅ **Supports pagination** for large histories  
✅ **Shows all payment details** including amounts, dates, Stripe IDs  
✅ **Can get individual invoice** details with `/v1/payments/me/invoice/{invoice_id}`

Perfect for building a "Payment History" or "My Invoices" page in your frontend! 💳📊