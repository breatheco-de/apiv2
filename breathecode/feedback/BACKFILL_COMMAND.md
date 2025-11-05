# Backfill Feedback Syllabus Command

## Quick Reference

Created a Django management command to backfill the `syllabus` field on existing `Answer` and `Review` records for backwards compatibility.

---

## Command Location

```
breathecode/feedback/management/commands/backfill_feedback_syllabus.py
```

---

## Quick Start

```bash
# 1. See what would be updated (dry run)
poetry run python manage.py backfill_feedback_syllabus --dry-run

# 2. Update all records
poetry run python manage.py backfill_feedback_syllabus
```

---

## What It Does

Populates the `syllabus` field based on this relationship:

```
Answer/Review → cohort → syllabus_version → syllabus
```

### Logic

1. Finds records where:
   - `cohort` is set
   - `syllabus` is NULL
   - `cohort.syllabus_version` exists
   - `cohort.syllabus_version.syllabus` exists

2. Updates:
   ```python
   record.syllabus = record.cohort.syllabus_version.syllabus
   ```

3. Skips records without proper cohort/syllabus_version chain

---

## Command Options

### `--dry-run`
Show what would be updated without making changes.

```bash
python manage.py backfill_feedback_syllabus --dry-run
```

**Use this first!** Always run a dry run before actual updates.

### `--model {answer|review|all}`
Choose which model to process (default: `all`).

```bash
# Update only answers
python manage.py backfill_feedback_syllabus --model answer

# Update only reviews
python manage.py backfill_feedback_syllabus --model review

# Update both (default)
python manage.py backfill_feedback_syllabus --model all
```

### `--limit <number>`
Limit the number of records processed.

```bash
# Process only 100 records
python manage.py backfill_feedback_syllabus --limit 100
```

---

## Usage Examples

### Example 1: Test with Small Batch

```bash
# Dry run with limit
poetry run python manage.py backfill_feedback_syllabus --dry-run --limit 10

# If looks good, process those 10
poetry run python manage.py backfill_feedback_syllabus --limit 10
```

### Example 2: Process Answers First

```bash
# Dry run answers only
poetry run python manage.py backfill_feedback_syllabus --model answer --dry-run

# Update answers
poetry run python manage.py backfill_feedback_syllabus --model answer
```

### Example 3: Batch Processing

```bash
# Process in batches of 1000
poetry run python manage.py backfill_feedback_syllabus --limit 1000

# Run again to process next batch
poetry run python manage.py backfill_feedback_syllabus --limit 1000

# Continue until no more records need updating
```

### Example 4: Production Run

```bash
# Step 1: Dry run to verify
poetry run python manage.py backfill_feedback_syllabus --dry-run

# Step 2: Test with small batch
poetry run python manage.py backfill_feedback_syllabus --limit 100

# Step 3: Verify results in database
# ... check database ...

# Step 4: Process all remaining
poetry run python manage.py backfill_feedback_syllabus
```

---

## Example Output

### Dry Run Output

```
DRY RUN MODE - No changes will be made
======================================================================
Processing Answer model...
======================================================================
Found 1523 Answer records to process
  [DRY RUN] Answer 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  [DRY RUN] Answer 2: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  [DRY RUN] Answer 3: cohort=santiago-ds-ft-1 → syllabus=data-science
  ...

Would update 1523 Answer records

======================================================================
Processing Review model...
======================================================================
Found 342 Review records to process
  [DRY RUN] Review 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  [DRY RUN] Review 2: cohort=bogota-web-dev-ft-2 → syllabus=full-stack
  ...

Would update 342 Review records

======================================================================
DRY RUN: Would update 1865 records in total
======================================================================
```

### Actual Run Output

```
======================================================================
Processing Answer model...
======================================================================
Found 1523 Answer records to process
  ✓ Answer 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ✓ Answer 2: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ✓ Answer 3: cohort=santiago-ds-ft-1 → syllabus=data-science
  ...

Updated 1523 Answer records

======================================================================
Processing Review model...
======================================================================
Found 342 Review records to process
  ✓ Review 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ✓ Review 2: cohort=bogota-web-dev-ft-2 → syllabus=full-stack
  ...

Updated 342 Review records

======================================================================
✓ Successfully updated 1865 records in total
======================================================================
```

### No Records to Update

```
======================================================================
Processing Answer model...
======================================================================
Found 0 Answer records to process
  No answers need updating

======================================================================
Processing Review model...
======================================================================
Found 0 Review records to process
  No reviews need updating

======================================================================
✓ Successfully updated 0 records in total
======================================================================
```

---

## When to Run

### After Migration

Run this command after applying the migration that adds the `syllabus` field:

```bash
# 1. Apply migration
poetry run python manage.py migrate feedback

# 2. Backfill existing data
poetry run python manage.py backfill_feedback_syllabus --dry-run
poetry run python manage.py backfill_feedback_syllabus
```

### Periodic Maintenance

Run periodically to catch any records where syllabus wasn't automatically set:

```bash
# Weekly/monthly maintenance
poetry run python manage.py backfill_feedback_syllabus
```

### After Data Import

If you import Answer/Review data from external sources:

```bash
# After import
poetry run python manage.py backfill_feedback_syllabus
```

---

## Error Handling

The command handles errors gracefully:

- Continues processing if individual records fail
- Shows first 5 errors
- Doesn't stop entire process due to single failure

Example error output:

```
Errors: 3
  - Answer 456: 'NoneType' object has no attribute 'syllabus'
  - Answer 789: Database constraint violation
  - Answer 1012: Invalid cohort reference
```

---

## Safety Features

### Idempotent

Safe to run multiple times:
- Only processes records where `syllabus` is NULL
- Already-updated records are automatically skipped
- No duplicate updates

### Dry Run

Always available to preview changes:
```bash
python manage.py backfill_feedback_syllabus --dry-run
```

### Efficient

- Uses `select_related()` to minimize queries
- Only updates the `syllabus` field (via `update_fields`)
- Processes records one at a time for error isolation

---

## Verification

After running the command, verify the results:

### SQL Query to Check

```sql
-- Check Answer records
SELECT 
    COUNT(*) as total_answers,
    COUNT(syllabus_id) as with_syllabus,
    COUNT(*) - COUNT(syllabus_id) as without_syllabus
FROM feedback_answer
WHERE cohort_id IS NOT NULL;

-- Check Review records
SELECT 
    COUNT(*) as total_reviews,
    COUNT(syllabus_id) as with_syllabus,
    COUNT(*) - COUNT(syllabus_id) as without_syllabus
FROM feedback_review
WHERE cohort_id IS NOT NULL;
```

### Django Shell Check

```python
from breathecode.feedback.models import Answer, Review

# Count answers needing backfill
needs_backfill = Answer.objects.filter(
    cohort__isnull=False,
    syllabus__isnull=True
).count()
print(f"Answers still needing backfill: {needs_backfill}")

# Count reviews needing backfill
needs_backfill = Review.objects.filter(
    cohort__isnull=False,
    syllabus__isnull=True
).count()
print(f"Reviews still needing backfill: {needs_backfill}")
```

---

## Troubleshooting

### Issue: Command shows 0 records to process

**Possible causes:**
1. All records already have syllabus set ✓
2. Records don't have cohorts set
3. Cohorts don't have syllabus_version set

**Check:**
```python
from breathecode.feedback.models import Answer

# How many answers have cohorts?
Answer.objects.filter(cohort__isnull=False).count()

# How many already have syllabus?
Answer.objects.filter(syllabus__isnull=False).count()

# How many need backfill?
Answer.objects.filter(
    cohort__isnull=False,
    syllabus__isnull=True
).count()
```

### Issue: Errors during processing

**Review the error messages:**
- `'NoneType' object has no attribute 'syllabus'` → Cohort has no syllabus_version
- Database errors → Check constraints and foreign keys
- Permission errors → Check database user permissions

### Issue: Some records not updated

**Possible reasons:**
1. Cohort has no syllabus_version
2. Syllabus_version has no syllabus
3. Database constraints prevent update

**Manual check:**
```python
answer = Answer.objects.get(id=123)
print(f"Cohort: {answer.cohort}")
print(f"Syllabus Version: {answer.cohort.syllabus_version if answer.cohort else None}")
print(f"Syllabus: {answer.cohort.syllabus_version.syllabus if answer.cohort and answer.cohort.syllabus_version else None}")
```

---

## Summary

✅ **Created:** Management command for backwards compatibility  
✅ **Purpose:** Backfill syllabus field from cohort relationships  
✅ **Safe:** Dry run, idempotent, error-tolerant  
✅ **Flexible:** Options for model selection, limits, dry runs  
✅ **Well-documented:** Comprehensive help and examples  

Run after migration to populate syllabus on existing records!

