# Auto-Normalization of Academy Features

## Overview

The system automatically normalizes `academy_features` for all academies during deployment. This means that when you add a new feature flag to `default_academy_features()`, all existing academies in the database will automatically be updated with the new default value.

## How It Works

### The Problem

Before this system, when you added a new feature flag:

```python
def default_academy_features():
    return {
        "features": {
            "allow_events": True,
            "new_feature": False,  # ← NEW FEATURE
        }
    }
```

Existing academies in the database would NOT have `new_feature` in their `academy_features` JSON field. They would only get it through the runtime merge in `get_academy_features()`, but the database would remain unchanged.

### The Solution

Now, a `post_migrate` signal automatically updates all academies:

```python
@receiver(post_migrate)
def normalize_academy_features_on_migrate(sender, **kwargs):
    """
    Automatically normalize academy_features for all academies after migrations.
    """
    # Only run for admissions app
    if sender.name != "breathecode.admissions":
        return
    
    # Update all academies with new features
    for academy in Academy.objects.all():
        merged_features = academy.get_academy_features()
        if merged_features != academy.academy_features:
            academy.academy_features = merged_features
            academy.save(update_fields=["academy_features"])
```

## When Does It Run?

The normalization runs automatically:

1. **During Deployment**: When you run `python manage.py migrate`
2. **After Any Migration**: But only for the `breathecode.admissions` app
3. **Silently**: It doesn't clutter deployment logs unless there are updates

## What Gets Updated?

### Example Scenario

**Before Deployment:**

```python
# default_academy_features() in code
{
    "features": {
        "allow_events": True,
        "allow_mentoring": True,
        "reseller": False  # ← NEW
    }
}

# Academy #1 in database
{
    "features": {
        "allow_events": True,
        "allow_mentoring": False  # ← Custom value
    }
}

# Academy #2 in database
{
    "features": {
        "allow_events": True,
        "allow_mentoring": True
    }
}
```

**After Deployment (migrate runs):**

```python
# Academy #1 in database - NEW feature added, custom values preserved
{
    "features": {
        "allow_events": True,
        "allow_mentoring": False,  # ← Preserved custom value
        "reseller": False  # ← NEW feature added with default
    }
}

# Academy #2 in database - NEW feature added
{
    "features": {
        "allow_events": True,
        "allow_mentoring": True,
        "reseller": False  # ← NEW feature added with default
    }
}
```

## Key Features

### ✅ Safe for Production

- **Non-Breaking**: Uses `get_academy_features()` which does deep merge
- **Preserves Custom Values**: Academy-specific settings are never overwritten
- **Error Handling**: Failures won't break migrations
- **Efficient**: Only updates academies with differences

### ✅ Developer Friendly

- **Zero Manual Work**: Just add the feature and deploy
- **Backwards Compatible**: Old code still works during transition
- **Predictable**: Same behavior as manual `normalize_academy_features` command

### ✅ DevOps Friendly

- **Automatic**: No extra deployment steps needed
- **Idempotent**: Safe to run multiple times
- **Silent**: Doesn't clutter logs unnecessarily
- **Fast**: Uses `update_fields` for efficiency

## Workflow

### Adding a New Feature Flag

1. **Add to defaults**:

```python
# breathecode/admissions/models.py
def default_academy_features():
    return {
        "features": {
            # ... existing features
            "my_new_feature": False,  # ← Add here
        }
    }
```

2. **Commit and push**:

```bash
git add breathecode/admissions/models.py
git commit -m "feat: add my_new_feature flag"
git push
```

3. **Deploy**:

```bash
# On server during deployment
python manage.py migrate  # ← Auto-normalization happens here!
```

4. **Done!** All academies now have `my_new_feature` in their database.

## Monitoring

### Check Logs

During deployment, you'll see:

```
INFO: Auto-normalizing academy_features after migration...
INFO: Successfully normalized academy_features for 42 academies
```

Or if no updates needed:

```
DEBUG: All academies already have current feature flags
```

### Manual Check

You can verify the normalization worked:

```bash
python manage.py shell
>>> from breathecode.admissions.models import Academy
>>> academy = Academy.objects.first()
>>> academy.academy_features
{'features': {'allow_events': True, 'my_new_feature': False, ...}, ...}
```

## Alternative: Manual Normalization

If you need to normalize before deployment (e.g., for testing):

```bash
# Preview what would change
python manage.py normalize_academy_features --dry-run

# Apply changes manually
python manage.py normalize_academy_features
```

This is the same logic that runs automatically during deployment.

## Technical Details

### Signal Details

- **Signal**: `django.db.models.signals.post_migrate`
- **Receiver**: `normalize_academy_features_on_migrate`
- **Location**: `breathecode/admissions/receivers.py`
- **App Filtering**: Only runs for `breathecode.admissions` migrations

### Performance

- **Query Optimization**: Uses `update_fields=["academy_features"]` for minimal DB impact
- **Selective Updates**: Only updates academies with differences
- **Bulk Processing**: Processes all academies in one migration run

### Error Handling

```python
try:
    # Normalization logic
except Exception as e:
    # Log error but don't fail migration
    logger.error(f"Error normalizing academy_features: {e}")
```

Errors are logged but won't break the deployment.

## Comparison: Before vs After

### Before (Manual Process)

```
Developer adds feature → Deploy → Notice academies missing feature
→ SSH to server → Run normalize_academy_features → Hope you didn't forget
```

Problems:
- ❌ Easy to forget
- ❌ Extra deployment step
- ❌ Inconsistent timing
- ❌ Risk of incomplete updates

### After (Automatic Process)

```
Developer adds feature → Deploy (migrate runs) → Done ✅
```

Benefits:
- ✅ Impossible to forget
- ✅ Zero extra steps
- ✅ Consistent every time
- ✅ Guaranteed complete updates

## Related Files

- **Signal**: `breathecode/admissions/receivers.py` (line ~278)
- **Model**: `breathecode/admissions/models.py` (`default_academy_features()` and `get_academy_features()`)
- **Command**: `breathecode/admissions/management/commands/normalize_academy_features.py`
- **Docs**: `breathecode/admissions/docs/ACADEMY_FEATURES.md`

## FAQ

**Q: What if a migration fails?**
A: The normalization uses try-except to avoid breaking migrations. Check logs for errors.

**Q: Can I disable this?**
A: Not recommended, but you could comment out the signal receiver. Better to fix any issues.

**Q: Does this slow down deployments?**
A: Minimal impact. It only updates academies with differences and uses efficient queries.

**Q: What about rollbacks?**
A: If you rollback code, the old features remain in the database (no harm). Next deploy will re-normalize.

**Q: Can I run this locally?**
A: Yes, every time you run `python manage.py migrate` locally, it will normalize your local DB.

**Q: What if I remove a feature?**
A: Old features remain in the database (no automatic cleanup). They're harmless but can be cleaned manually.

## Best Practices

1. **Always add features with defaults**: Don't remove old features without planning
2. **Test locally first**: Run migrations locally to verify behavior
3. **Monitor logs**: Check deployment logs to confirm normalization
4. **Document features**: Update `ACADEMY_FEATURES.md` when adding features
5. **Use meaningful defaults**: Choose defaults that make sense for most academies

