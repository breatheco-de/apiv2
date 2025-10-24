# Django Groups in Fixtures - Guide

## Available Groups

After running `python manage.py set_permissions`, these groups are created:

1. **Admin** - All permissions (966 permissions)
2. **Default** - Basic permissions for all users
3. **Student** - Student-specific permissions
4. **Creator** - Can create packages and manage organizations
5. **Teacher** - Can add code reviews
6. **Geek Creator** - Inherits from Teacher
7. **Mentor** - Can join mentorships
8. **Mentorships** - Mentorship access
9. **Events** - Event access
10. **Classes** - Live class access
11. **Legacy** - Backwards compatibility
12. **Paid Student** - Access to private links

## How to Assign Groups in Fixtures

### Method 1: In JSON Fixtures (Manual)

To assign groups to a user in fixtures, you need to reference the group's **primary key** (integer ID):

```json
{
    "model": "auth.user",
    "pk": 1,
    "fields": {
        "username": "aalejo@gmail.com",
        "email": "aalejo@gmail.com",
        "first_name": "Alejandro",
        "last_name": "Sanchez",
        "is_superuser": true,
        "is_staff": true,
        "groups": [1],  // ← Group PKs (1 = Admin group)
        "user_permissions": []
    }
}
```

**Important:** You need to know the group's PK, which is assigned when the group is created. This makes fixtures brittle.

### Method 2: Use Management Commands (Recommended)

Instead of hardcoding group IDs in fixtures, use management commands after loading fixtures:

```bash
# 1. Load fixtures
poetry run python manage.py loaddata breathecode/admissions/fixtures/dev_user.json
poetry run python manage.py loaddata breathecode/admissions/fixtures/dev_data.json

# 2. Assign groups
poetry run python manage.py assign_staff_groups
```

### Method 3: Combined Fixture Loading

Use the integrated command that does everything:

```bash
poetry run python manage.py load_dev_fixtures --flush
```

This automatically:
1. Flushes the database
2. Loads user fixtures
3. Loads admissions fixtures
4. Creates UserInvite records for staff
5. Assigns Admin group to all staff users

## Management Commands

### assign_staff_groups

Assign groups to staff users programmatically:

```bash
# Assign Admin group to all staff (default)
poetry run python manage.py assign_staff_groups

# Assign specific group
poetry run python manage.py assign_staff_groups --group="Creator"

# Only assign to superusers
poetry run python manage.py assign_staff_groups --superusers-only

# Force reassign even if already has group
poetry run python manage.py assign_staff_groups --force
```

### create_staff_invites

Create UserInvite records for staff users:

```bash
# Create invites for staff users
poetry run python manage.py create_staff_invites

# Update existing invites to ACCEPTED
poetry run python manage.py create_staff_invites --force
```

## Verifying Group Assignments

Check which groups a user has:

```python
from django.contrib.auth.models import User

user = User.objects.get(email='your@email.com')
print([g.name for g in user.groups.all()])
```

Or use Django admin at `/admin/auth/user/` to view and edit group assignments.

## Why Not Hardcode in Fixtures?

1. **Group PKs are unstable** - They depend on creation order
2. **Different environments** - Dev vs staging vs production may have different group IDs
3. **Maintenance** - Hard to update when groups change
4. **Readability** - Group names are clearer than IDs

## Best Practice

✅ **Do this:**
- Load basic user data from fixtures
- Use management commands to assign groups
- Keep group logic in code, not JSON

❌ **Don't do this:**
- Hardcode group IDs in fixtures
- Rely on specific group PKs across environments

## Current Status

After running the setup, all 12 staff users have:
- ✅ Admin group assigned
- ✅ UserInvite with ACCEPTED status
- ✅ Email validated
- ✅ Ready to use the platform
