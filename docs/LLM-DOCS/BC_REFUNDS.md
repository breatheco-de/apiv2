# 💰 Refunds System

## 📋 Overview

The refunds system allows processing full or partial refunds of invoices. When a refund is processed, a **CreditNote** (credit note) is created to document the refund and the invoice status is updated. The system also handles integration with Stripe to process refunds for credit card payments.

## 🏗️ System Architecture

### Main Models

#### 1. Invoice
The invoice represents a payment made by a user. Fields relevant for refunds:

- `amount`: Total invoice amount
- `amount_refunded`: Total amount already refunded
- `status`: Invoice status (can be `FULFILLED`, `PARTIALLY_REFUNDED`, `REFUNDED`)
- `refunded_at`: Date when the invoice was fully refunded
- `refund_stripe_id`: Stripe refund ID (if applicable)
- `stripe_id`: Stripe charge ID
- `amount_breakdown`: Breakdown of how the amount is divided between plans and services

**Invoice statuses related to refunds:**
- `FULFILLED`: Invoice fully paid
- `PARTIALLY_REFUNDED`: Invoice partially refunded
- `REFUNDED`: Invoice fully refunded

#### 2. CreditNote
Represents a processed refund. Each refund creates a CreditNote.

**Main fields:**
- `invoice`: Associated invoice (ForeignKey)
- `amount`: Refund amount
- `currency`: Refund currency
- `reason`: Refund reason
- `status`: Credit note status (`DRAFT`, `ISSUED`, `CANCELLED`)
- `issued_at`: Issue date
- `legal_text`: Country-specific legal text
- `country_code`: Country code for legal compliance
- `breakdown`: Breakdown of what is being refunded (plans, service-items)
- `refund_stripe_id`: Stripe refund ID (if applicable)

**Relationship:**
- An Invoice can have multiple CreditNotes (for partial refunds)
- Each CreditNote is linked to an Invoice

## 🔄 Refund Processing Flow

### 1. API Endpoint

```bash
POST /v1/payments/academy/invoice/{invoice_id}/refund
Headers: Academy: {academy_id}
```

**Permission requirements:** `crud_invoice`

### 2. Request Parameters

```json
{
  "refund_amount": 100.00,
  "items_to_refund": {
    "plan-slug-1": 60.00,
    "service-slug-1": 40.00
  },
  "reason": "Customer requested refund"
}
```

**Required fields:**
- `refund_amount` (float): Total amount to refund (must match the sum of `items_to_refund`)
- `items_to_refund` (dict): Dictionary mapping slugs to refund amounts
  - Keys are plan or service slugs
  - Values are the amounts to refund for each item
- `reason` (string, optional): Refund reason

### 3. Validations

The system performs the following validations:

1. **Invoice exists and belongs to the academy**
2. **Invoice is not fully refunded**
3. **Valid refund amount:**
   - Must be greater than 0
   - Cannot exceed available amount (`invoice.amount - invoice.amount_refunded`)
4. **Valid items_to_refund:**
   - Must be a non-empty dictionary
   - All slugs must exist in `invoice.amount_breakdown`
   - All amounts must be positive numbers
   - Amounts cannot exceed original amounts for each item
5. **Amount matching:**
   - `refund_amount` must match the sum of all values in `items_to_refund` (with 0.01 tolerance for floating point differences)
6. **Invoice status:**
   - Only invoices with status `FULFILLED`, `PARTIALLY_REFUNDED`, or `REFUNDED` can be refunded

### 4. Processing

The refund process follows these steps:

#### Step 1: Calculate Refund Breakdown
```python
calculate_refund_breakdown(invoice, refund_amount, items_to_refund, lang)
```

This function:
- Validates that all slugs exist in `invoice.amount_breakdown`
- Validates that amounts don't exceed originals
- Generates a breakdown with the structure:
```json
{
  "plans": {
    "plan-slug-1": {
      "amount": 60.00,
      "currency": "USD",
      ...
    }
  },
  "service-items": {
    "service-slug-1": {
      "amount": 40.00,
      "currency": "USD",
      "how-many": 1,
      "unit-type": "UNIT",
      ...
    }
  }
}
```

#### Step 2: Process Refund in Stripe (if applicable)
If the invoice has `stripe_id`:
- Calls `stripe_service.refund_payment(invoice, amount=amount)`
- Gets the `refund_stripe_id` from Stripe
- Automatically updates `invoice.amount_refunded` and `invoice.status`

If the invoice does NOT have `stripe_id`:
- Manually updates `invoice.amount_refunded`
- Updates `invoice.status` to `PARTIALLY_REFUNDED` or `REFUNDED` as appropriate

#### Step 3: Create CreditNote
A `CreditNote` record is created with:
- Reference to the invoice
- Amount, currency, reason
- Refund breakdown
- `refund_stripe_id` (if applicable)
- Status `ISSUED`

#### Step 4: Deprecate Plans and Remove Services
If plans are being refunded:
- Finds all active `Subscription` for the user with those plans
- Changes them to `EXPIRED` status with explanatory message
- Finds all active `PlanFinancing` for the user with those plans
- Changes them to `EXPIRED` status with explanatory message

If service-items are being refunded:
- Deletes associated `SubscriptionServiceItem`
- Deletes associated `PlanServiceItemHandler`

## 📝 Main Functions

### `calculate_refund_breakdown()`

**Location:** `breathecode/payments/actions.py`

**Purpose:** Calculates which invoice components should be refunded based on the amount and specified items.

**Parameters:**
- `invoice` (Invoice): The invoice to refund
- `refund_amount` (float): Total amount to refund
- `items_to_refund` (dict[str, float]): Dictionary mapping slugs to amounts
- `lang` (str): Language code for error messages

**Returns:**
- `dict[str, Any]`: Refund breakdown with plans and service-items structure

**Validations:**
- Invoice must have `amount_breakdown`
- Amount must be greater than 0
- Amount cannot exceed available
- All slugs must exist in breakdown
- Amounts per item cannot exceed originals
- Total amount must match sum of items

### `process_refund()`

**Location:** `breathecode/payments/actions.py`

**Purpose:** Processes a complete refund: creates the CreditNote, processes payment in Stripe (if applicable), and deprecates plans/removes services.

**Parameters:**
- `invoice` (Invoice): The invoice to refund
- `amount` (float): Total amount to refund (required)
- `items_to_refund` (dict[str, float]): Dictionary mapping slugs to amounts (required)
- `breakdown` (dict, optional): Refund breakdown (calculated if not provided)
- `reason` (str): Refund reason
- `country_code` (str, optional): Country code
- `legal_text` (str, optional): Country-specific legal text
- `lang` (str): Language code

**Returns:**
- `CreditNote`: The created CreditNote object

**Side effects:**
- Creates a refund in Stripe (if applicable)
- Updates `invoice.amount_refunded` and `invoice.status`
- Creates a `CreditNote` record
- Expires associated subscriptions and plan financings
- Deletes associated service items

### `refund_payment()` (Stripe Service)

**Location:** `breathecode/payments/services/stripe.py`

**Purpose:** Processes a refund through the Stripe API.

**Parameters:**
- `invoice` (Invoice): The invoice to refund
- `amount` (float, optional): Amount to refund (if None, refunds full available amount)

**Returns:**
- `dict`: Contains `refund`, `refunded_amount`, and `invoice`

**Validations:**
- Amount cannot exceed available
- Amount must be greater than 0
- Invoice must have `stripe_id`

## 🔌 Stripe Integration

### Stripe Refund Flow

1. **Validation:** Verifies that the invoice has `stripe_id`
2. **Refund Creation:** Calls `stripe.Refund.create()` with:
   - `charge`: The invoice's `stripe_id`
   - `amount`: The amount in cents (if partial refund)
3. **Invoice Update:** Stripe automatically updates:
   - `invoice.amount_refunded`
   - `invoice.refund_stripe_id` (or accumulates if already exists)
   - `invoice.status` (to `PARTIALLY_REFUNDED` or `REFUNDED`)
4. **CreditNote Creation:** Only after successful Stripe refund

### Multiple Refunds

The system supports multiple partial refunds:
- Each refund creates a new `CreditNote`
- `invoice.amount_refunded` accumulates
- `invoice.refund_stripe_id` may contain the last refund ID (Stripe handles multiple refunds internally)
- Status changes to `REFUNDED` when `amount_refunded >= amount`

## 📊 Serializers

### CreditNoteSerializer

**Location:** `breathecode/payments/serializers.py`

**Serialized fields:**
- `id`: Credit note ID
- `amount`: Refund amount
- `currency`: Currency (serialized with `GetCurrencySmallSerializer`)
- `reason`: Refund reason
- `issued_at`: Issue date
- `status`: Status (`DRAFT`, `ISSUED`, `CANCELLED`)
- `legal_text`: Legal text
- `country_code`: Country code
- `breakdown`: Refund breakdown
- `refund_stripe_id`: Stripe ID
- `created_at`, `updated_at`: Timestamps
- `invoice`: Associated invoice (serialized with `GetInvoiceSmallSerializer`)
- `invoice_credit_notes`: All credit notes for the invoice (method field)

### GetInvoiceSerializer

Includes refund-related fields:
- `amount_refunded`: Total refunded amount
- `refund_stripe_id`: Stripe refund ID
- `refunded_at`: Full refund date
- `credit_notes`: List of all associated credit notes

## 🎯 Use Cases

### Case 1: Full Invoice Refund

```json
POST /v1/payments/academy/invoice/123/refund
{
  "refund_amount": 99.99,
  "items_to_refund": {
    "monthly-plan": 99.99
  },
  "reason": "Customer cancellation"
}
```

**Result:**
- A CreditNote is created for $99.99
- Invoice status changes to `REFUNDED`
- If there's an active Subscription with that plan, it expires
- Refund is processed in Stripe (if applicable)

### Case 2: Partial Refund of Multiple Items

```json
POST /v1/payments/academy/invoice/123/refund
{
  "refund_amount": 50.00,
  "items_to_refund": {
    "monthly-plan": 30.00,
    "mentoring-service": 20.00
  },
  "reason": "Partial refund for service issues"
}
```

**Result:**
- A CreditNote is created for $50.00
- Invoice status changes to `PARTIALLY_REFUNDED`
- $30 is refunded from the plan and $20 from the service
- Plan subscription expires
- Mentoring service items are deleted

### Case 3: Multiple Partial Refunds

First refund:
```json
POST /v1/payments/academy/invoice/123/refund
{
  "refund_amount": 30.00,
  "items_to_refund": {"plan-slug": 30.00}
}
```

Second refund (later):
```json
POST /v1/payments/academy/invoice/123/refund
{
  "refund_amount": 20.00,
  "items_to_refund": {"service-slug": 20.00}
}
```

**Result:**
- 2 separate CreditNotes are created
- `invoice.amount_refunded` = 50.00
- If invoice total is $100, it remains in `PARTIALLY_REFUNDED` status
- If total is $50, it changes to `REFUNDED` after the second refund

## ⚠️ Validations and Common Errors

### Validation Errors

1. **"Invoice has already been fully refunded"**
   - Occurs when `invoice.amount_refunded >= invoice.amount`
   - Solution: Check invoice status before attempting to refund

2. **"Refund amount exceeds available amount to refund"**
   - Requested amount exceeds `invoice.amount - invoice.amount_refunded`
   - Solution: Correctly calculate available amount

3. **"Invalid slugs provided"**
   - Slugs in `items_to_refund` don't exist in `invoice.amount_breakdown`
   - Solution: Verify available slugs in the invoice

4. **"Refund amount does not match the sum of items_to_refund amounts"**
   - `refund_amount` doesn't match the sum of values in `items_to_refund`
   - Solution: Ensure amounts sum exactly to `refund_amount`

5. **"Refund amount for '{slug}' exceeds its original amount"**
   - Attempting to refund more than an item originally cost
   - Solution: Verify original amounts in `invoice.amount_breakdown`

6. **"Only fulfilled or partially refunded invoices can be refunded"**
   - Invoice is not in a valid state for refunding
   - Solution: Only invoices with status `FULFILLED`, `PARTIALLY_REFUNDED`, or `REFUNDED` can be refunded

### Stripe Errors

If there's an error processing the refund in Stripe:
- Error is logged
- An exception is raised that stops the process
- CreditNote is NOT created
- Invoice is NOT updated

## 🔍 Related Queries and Endpoints

### View Credit Notes for an Invoice

Credit notes are included in the Invoice serializer:
```bash
GET /v1/payments/academy/invoice/{invoice_id}
```

Response includes:
```json
{
  "credit_notes": [
    {
      "id": 1,
      "amount": 50.00,
      "reason": "Partial refund",
      "status": "ISSUED",
      ...
    }
  ]
}
```

### View All Credit Notes

Each CreditNote includes all credit notes for its invoice in `invoice_credit_notes`:
```json
{
  "invoice_credit_notes": [
    {
      "id": 1,
      "amount": 30.00,
      ...
    },
    {
      "id": 2,
      "amount": 20.00,
      ...
    }
  ]
}
```

## 🧪 Testing

### Recommended Tests

1. **Full refund test:**
   - Create invoice with plan
   - Process full refund
   - Verify CreditNote created
   - Verify invoice.status = REFUNDED
   - Verify subscription expired

2. **Partial refund test:**
   - Create invoice with multiple items
   - Process partial refund
   - Verify CreditNote with correct amount
   - Verify invoice.status = PARTIALLY_REFUNDED
   - Verify only specified items were affected

3. **Validation tests:**
   - Attempt to refund more than available
   - Attempt to refund with invalid slugs
   - Attempt to refund already fully refunded invoice
   - Attempt to refund with non-matching amounts

4. **Stripe integration test:**
   - Mock Stripe refund
   - Verify refund_stripe_id saved
   - Verify invoice update

## 📚 Code References

### Main Files

- **Models:** `breathecode/payments/models.py`
  - `Invoice` (lines 1750-1876)
  - `CreditNote` (lines 1878-1930)

- **Actions:** `breathecode/payments/actions.py`
  - `calculate_refund_breakdown()` (lines 2462-2626)
  - `process_refund()` (lines 2629-2828)

- **Views:** `breathecode/payments/views.py`
  - `AcademyInvoiceRefundView` (lines 2102-2273)

- **Services:** `breathecode/payments/services/stripe.py`
  - `refund_payment()` (lines 440-524)

- **Serializers:** `breathecode/payments/serializers.py`
  - `CreditNoteSerializer` (lines 923-949)
  - `GetInvoiceSerializer` (lines 951-980)

- **URLs:** `breathecode/payments/urls/v1.py`
  - Endpoint: line 138

## 🎓 Best Practices

1. **Always validate before processing:**
   - Verify invoice exists and is in valid state
   - Calculate available amount before requesting refund
   - Verify slugs exist in breakdown

2. **Error handling:**
   - Catch Stripe exceptions
   - Log errors for debugging
   - Provide clear error messages to user

3. **Transactions:**
   - Refund process should be atomic
   - If Stripe refund fails, don't create CreditNote
   - If CreditNote creation fails, revert invoice changes

4. **Documentation:**
   - Always include a clear reason for the refund
   - Maintain logs of all processed refunds
   - Record who processed the refund (user/admin)

5. **Testing:**
   - Test full and partial refunds
   - Test multiple partial refunds
   - Test amount and slug validations
   - Test Stripe integration (mocks)

## 🔐 Security

- Only users with `crud_invoice` permission can process refunds
- Validations prevent duplicate or excessive refunds
- Stripe refunds require API key authentication
- All errors are translated using Capy Core's i18n system

## 📝 Additional Notes

- The system supports refunds for both Stripe payments and external payments
- Partial refunds allow flexibility in cases of disputes or issues with specific services
- Refund breakdown is stored in CreditNote for audit purposes
- Subscriptions and plan financings are automatically expired when their plans are refunded
- Service items are deleted when refunded
