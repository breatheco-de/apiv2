# Academy Owner - Implementation Summary

## Overview

Implemented a hybrid signal-based approach for managing academy ownership and admin access.

## How It Works

### 1. Owner Field (Academy Model)

```python
class Academy(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_academies",
        help_text="Primary owner of the academy",
        db_index=True,
    )
```

### 2. Owner Assignment (View Layer)

When a new academy is created via API:

```python
# In AcademyListView.post()
academy = serializer.save(owner=request.user)
```

The view sets `owner=request.user`, giving the creator ownership.

### 3. ProfileAcademy Creation (Signal Layer)

When an academy is saved with an owner, the signal automatically creates ProfileAcademy:

```python
# In breathecode/admissions/receivers.py
@receiver(academy_saved, sender=Academy)
def create_owner_profile_academy(sender, instance, created, **kwargs):
    if created and instance.owner:
        # Creates ProfileAcademy with admin role
        ProfileAcademy.objects.get_or_create(
            user=instance.owner,
            academy=instance,
            defaults={
                'role': admin_role,
                'status': 'ACTIVE',
                ...
            }
        )
```

## Benefits of This Approach

### ✅ Separation of Concerns
- **View**: Sets the owner (has access to `request.user`)
- **Signal**: Creates ProfileAcademy (domain logic)

### ✅ Works Everywhere
- ✓ API creates academy → signal creates ProfileAcademy
- ✓ Django Admin creates academy → signal creates ProfileAcademy (if owner set)
- ✓ Fixtures/migrations → signal creates ProfileAcademy (if owner populated)
- ✓ Management commands → signal creates ProfileAcademy

### ✅ DRY (Don't Repeat Yourself)
- ProfileAcademy creation logic in one place
- No need to duplicate across views
- Consistent behavior system-wide

### ✅ Maintainable
- Easy to test (signal tested separately)
- Clear responsibility boundaries
- Easy to modify or extend

## Usage

### Creating an Academy via API

```bash
POST /v1/admissions/academy
Authorization: Token <your-token>

{
  "slug": "new-academy",
  "name": "New Academy",
  "logo_url": "https://example.com/logo.png",
  "street_address": "123 Main St",
  "city": 1,
  "country": "us"
}
```

**What Happens:**
1. View validates and creates academy
2. View sets `academy.owner = request.user`
3. Academy.save() is called
4. `academy_saved` signal fires
5. Signal sees `created=True` and `instance.owner` is set
6. Signal creates ProfileAcademy with admin role
7. Creator now owns and can manage the academy!

### Checking Ownership

```python
# Get academy owner
academy = Academy.objects.get(slug='my-academy')
print(academy.owner.email)  # "creator@example.com"

# Get all academies owned by a user
user = User.objects.get(email='creator@example.com')
owned_academies = user.owned_academies.all()
```

### API Response

```json
{
  "id": 1,
  "slug": "new-academy",
  "name": "New Academy",
  "owner": {
    "id": 123,
    "email": "creator@example.com"
  },
  ...
}
```

## Migrations

1. **0005_add_owner_to_academy.py** - Adds owner field
2. **0006_populate_academy_owner.py** - Populates existing academies

## Management Commands

### populate_academy_owners

Populate or update academy owners from ProfileAcademy:

```bash
# Populate owners for academies without owners
poetry run python manage.py populate_academy_owners

# Force update all academies
poetry run python manage.py populate_academy_owners --force
```

This finds the first active admin for each academy and sets them as owner.

## Files Modified

### Core Implementation:
- `breathecode/admissions/models.py` - Added owner field
- `breathecode/admissions/views.py` - Sets owner on creation
- `breathecode/admissions/receivers.py` - Signal creates ProfileAcademy
- `breathecode/admissions/serializers.py` - Includes owner in response

### Migrations:
- `breathecode/admissions/migrations/0005_add_owner_to_academy.py`
- `breathecode/admissions/migrations/0006_populate_academy_owner.py`

### Commands:
- `breathecode/admissions/management/commands/populate_academy_owners.py`
- `breathecode/admissions/management/commands/load_dev_fixtures.py` (updated)

### Tests:
- `breathecode/admissions/tests/urls/tests_academy.py` - Added tests

### Documentation:
- `docs/essential/academy-owner.md`
- `breathecode/admissions/ACADEMY_OWNER_IMPLEMENTATION.md` (this file)

## Testing

All tests passing (12/12):

```bash
poetry run pytest breathecode/admissions/tests/urls/tests_academy.py -v
```

Includes specific test for signal functionality:
- `test_academy_creation_signal_creates_profile_academy` - Verifies signal creates ProfileAcademy

## Signal Flow Diagram

```
User creates academy via API
    ↓
AcademyListView.post()
    ↓
serializer.save(owner=request.user)  ← Sets owner
    ↓
Academy.save() called
    ↓
academy_saved signal fires (created=True, instance.owner set)
    ↓
create_owner_profile_academy receiver runs
    ↓
ProfileAcademy created with admin role
    ↓
Creator is now academy owner AND admin!
```

## Edge Cases Handled

1. **No admin role exists**: Signal logs warning and returns gracefully
2. **Owner already has ProfileAcademy**: `get_or_create` prevents duplicates
3. **Academy without owner**: Signal doesn't run (owner=None)
4. **Academy updated (not created)**: Signal only runs on creation

## Production Readiness

✅ Fully tested
✅ No linter errors
✅ Backwards compatible (owner nullable)
✅ Works with existing fixtures
✅ Signal properly registered
✅ Logging in place
✅ Error handling

## Next Steps (Optional)

1. Add owner to other academy serializers if needed
2. Add owner filtering to academy list endpoints
3. Create endpoint to transfer ownership
4. Add owner change history tracking

---

**Status**: ✅ **Production Ready** - Signal-based implementation complete!
