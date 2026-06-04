# Feedback Management Commands

## backfill_feedback_syllabus

Backfills the `syllabus` field on `Answer` and `Review` models based on their cohort's syllabus_version.

### Purpose

This command is designed for backwards compatibility after adding the `syllabus` field to Answer and Review models. It automatically populates the syllabus based on the relationship:

```
Answer/Review → cohort → syllabus_version → syllabus
```

### Usage

#### Basic Usage

```bash
# Dry run (shows what would be updated without making changes)
python manage.py backfill_feedback_syllabus --dry-run

# Update all Answer and Review records
python manage.py backfill_feedback_syllabus
```

#### Options

**`--dry-run`**  
Shows what would be updated without making any database changes. Always run this first to verify the command will work as expected.

```bash
python manage.py backfill_feedback_syllabus --dry-run
```

**`--model {answer|review|all}`**  
Specifies which model to process. Default is `all`.

```bash
# Update only Answer records
python manage.py backfill_feedback_syllabus --model answer

# Update only Review records
python manage.py backfill_feedback_syllabus --model review

# Update both (default)
python manage.py backfill_feedback_syllabus --model all
```

**`--limit <number>`**  
Limits the number of records to process. Useful for testing or batch processing.

```bash
# Process only 100 records
python manage.py backfill_feedback_syllabus --limit 100

# Process 50 answers only
python manage.py backfill_feedback_syllabus --model answer --limit 50
```

### What It Does

1. **Finds eligible records:**
   - Records with a `cohort` set
   - Records with `syllabus` not set (NULL)
   - Cohort has a `syllabus_version`
   - Syllabus_version has a `syllabus`

2. **Updates records:**
   - Sets `syllabus = cohort.syllabus_version.syllabus`
   - Uses `update_fields=['syllabus']` for efficiency
   - Handles errors gracefully

3. **Provides detailed output:**
   - Shows progress for each record
   - Displays summary statistics
   - Reports any errors encountered

### Example Output

```
======================================================================
Processing Answer model...
======================================================================
Found 1523 Answer records to process
  ✓ Answer 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ✓ Answer 2: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ✓ Answer 3: cohort=santiago-data-science-ft-1 → syllabus=data-science
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

### Dry Run Output

When using `--dry-run`, the output shows what would happen:

```
DRY RUN MODE - No changes will be made
======================================================================
Processing Answer model...
======================================================================
Found 1523 Answer records to process
  [DRY RUN] Answer 1: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  [DRY RUN] Answer 2: cohort=miami-web-dev-pt-1 → syllabus=full-stack
  ...

Would update 1523 Answer records

======================================================================
DRY RUN: Would update 1865 records in total
======================================================================
```

### When to Use

- **After migration:** Run this after applying the `0004_add_feedback_tags_and_optional_fields` migration
- **Data cleanup:** Periodically to catch any records where syllabus wasn't set
- **Testing:** Use `--dry-run` and `--limit` to test before full execution

### Error Handling

The command continues processing even if individual records fail. Errors are:
- Logged to output
- Limited to showing first 5 errors (to avoid overwhelming output)
- Do not stop the entire process

Example error output:
```
Errors: 3
  - Answer 456: 'NoneType' object has no attribute 'syllabus'
  - Answer 789: Database constraint violation
  - Answer 1012: Invalid cohort reference
```

### Performance Considerations

- Uses `select_related` to minimize database queries
- Processes records one at a time for better error isolation
- Use `--limit` for very large datasets to process in batches
- Use `--model` to process Answer and Review separately if needed

### Best Practices

1. **Always dry run first:**
   ```bash
   python manage.py backfill_feedback_syllabus --dry-run
   ```

2. **Test with a limit:**
   ```bash
   python manage.py backfill_feedback_syllabus --limit 10
   ```

3. **Process in batches for large datasets:**
   ```bash
   # First batch
   python manage.py backfill_feedback_syllabus --limit 1000
   
   # Verify results, then continue...
   python manage.py backfill_feedback_syllabus --limit 1000
   ```

4. **Separate models for debugging:**
   ```bash
   # Process answers first
   python manage.py backfill_feedback_syllabus --model answer
   
   # Then reviews
   python manage.py backfill_feedback_syllabus --model review
   ```

### Idempotency

The command is **idempotent** - it can be run multiple times safely:
- Only processes records where `syllabus` is NULL
- Already-updated records are skipped
- No duplicate updates or data corruption

### Related Models

This command updates:
- `breathecode.feedback.models.Answer`
- `breathecode.feedback.models.Review`

Based on data from:
- `breathecode.admissions.models.Cohort`
- `breathecode.admissions.models.SyllabusVersion`
- `breathecode.admissions.models.Syllabus`

---

## garbagecollect_answers

(Existing command - see separate documentation)

