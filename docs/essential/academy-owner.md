# Academy Owner Field

## Overview

The `owner` field has been added to the `Academy` model to explicitly track who owns/manages each academy.

## Model Field

```python
class Academy(models.Model):
    # ... other fields ...

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="owned_academies",
        help_text="Primary owner of the academy, typically the first admin with role 'admin'",
        db_index=True,
    )
```

## How It Works

### Automatic Population

The owner is automatically set to the **first active admin** from `ProfileAcademy` for that academy:

```python
from breathecode.authenticate.models import ProfileAcademy, Role

# Find first admin for an academy
first_admin = ProfileAcademy.objects.filter(
    academy=academy,
    role__slug='admin',
    status='ACTIVE'
).order_by('created_at').first()

academy.owner = first_admin.user
academy.save()
```

### Management Command

To populate or update academy owners:

```bash
# Populate owners for all academies
poetry run python manage.py populate_academy_owners

# Force update even if owner is already set
poetry run python manage.py populate_academy_owners --force
```

## Usage

### Get Academy Owner

```python
from breathecode.admissions.models import Academy

academy = Academy.objects.get(slug='downtown-miami')
if academy.owner:
    print(f"Owner: {academy.owner.email}")
    print(f"Name: {academy.owner.first_name} {academy.owner.last_name}")
```

### Get All Academies Owned by a User

```python
from django.contrib.auth.models import User

user = User.objects.get(email='aalejo@gmail.com')
owned_academies = user.owned_academies.all()

for academy in owned_academies:
    print(f"- {academy.name}")
```

### Filter Academies by Owner

```python
# Get all academies owned by a specific user
academies = Academy.objects.filter(owner__email='aalejo@gmail.com')

# Get academies without an owner
unowned = Academy.objects.filter(owner__isnull=True)
```

## Migrations

Two migrations were created:

1. **0005_add_owner_to_academy.py** - Adds the owner field to the Academy model
2. **0006_populate_academy_owner.py** - Data migration to populate existing academies

The data migration runs automatically and populates the owner field based on the first active admin from ProfileAcademy.

## Fixture Loading

When using the integrated fixture loading command, academy owners are automatically populated:

```bash
poetry run python manage.py load_dev_fixtures --flush
```

This command automatically:
1. Loads user fixtures
2. Loads academy fixtures
3. Creates ProfileAcademy relationships
4. Populates academy owners

## Important Notes

1. **Nullable Field**: The owner field is nullable (`null=True, blank=True`) so academies without admins won't cause errors.

2. **SET_NULL on Delete**: If the owner user is deleted, the owner field is set to NULL (`on_delete=models.SET_NULL`), preserving the academy.

3. **First Admin Logic**: The owner is determined by the **earliest created** ProfileAcademy record with role='admin' and status='ACTIVE'.

4. **Manual Override**: You can manually set any user as the owner through Django admin or code:
   ```python
   academy.owner = some_user
   academy.save()
   ```

## API Access

The owner can be included in API responses by adding it to serializers:

```python
from breathecode.authenticate.serializers import UserSmallSerializer

class AcademySerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    owner = UserSmallSerializer(required=False)
```

## Related Models

- **ProfileAcademy**: Links users to academies with specific roles
- **Role**: Defines capabilities (admin, staff, student, etc.)
- **AcademyAuthSettings**: Contains technical owners for GitHub/Google Cloud integrations

## See Also

- [ProfileAcademy Documentation](../advanced/profile-academy.md)
- [Roles and Capabilities](../security/roles.md)
- [Fixture Loading](../getting-started/fixtures.md)
