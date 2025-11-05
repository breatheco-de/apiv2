# Role Hierarchy and Priorities

## Overview

The BreatheCode API uses a role-based access control system where roles can inherit capabilities from other roles. This creates a hierarchy that determines permission levels and role upgrade logic.

## Role Priority Calculation

Role priorities are **automatically calculated** from the role inheritance hierarchy defined in `breathecode/authenticate/role_definitions.py`. Higher priority means more permissions.

### How Priority is Calculated

Priority is calculated as the **depth in the inheritance tree**:

- **Base roles** (don't extend anything): Priority = 1
- **Extended roles**: Priority = 1 + max(parent priorities)

### Example Hierarchy

```
student (priority 1)
  └─ (base role, no inheritance)

staff (priority 1)
  └─ (base role, no inheritance)
    └─ assistant (priority 2)
       ├─ homework_reviewer (priority 3)
       └─ teacher (priority 3)
          └─ academy_coordinator (priority 4)
             └─ country_manager (priority 5)
```

## ProfileAcademy Role Management

When a user is added to a cohort or academy, the system ensures:

1. **One ProfileAcademy per user per academy** (no duplicates)
2. **Automatic role upgrades** based on priority
3. **No downgrades** - higher roles are preserved

### Upgrade Logic

```python
if new_priority > current_priority:
    # Upgrade to the higher role
    profile.role = new_role
else:
    # Keep the current higher role
    pass
```

### Examples

| Current Role | New Role | Action | Reason |
|--------------|----------|--------|--------|
| student (1) | teacher (3) | ✓ Upgrade | Teacher has higher priority |
| assistant (2) | teacher (3) | ✓ Upgrade | Teacher has higher priority |
| teacher (3) | student (1) | ✗ Keep teacher | Teacher has higher priority |
| homework_reviewer (3) | teacher (3) | ✗ Keep current | Same priority |

## Implementation

### Central Role Definitions

All roles and capabilities are defined in:
```
breathecode/authenticate/role_definitions.py
```

This module provides:
- `CAPABILITIES`: List of all system capabilities
- `BASE_ROLES`: Foundation roles without inheritance
- `get_extended_roles()`: Complete role list with inheritance
- `get_role_priority(role_slug)`: Calculate priority for a role
- `get_all_role_priorities()`: Get priorities for all roles

### Usage in Code

```python
from breathecode.authenticate.role_definitions import get_role_priority

# Get priority of a role
priority = get_role_priority("teacher")  # Returns 3

# Compare roles for upgrade decision
current_priority = get_role_priority(current_role.slug)
new_priority = get_role_priority(new_role_slug)

if new_priority > current_priority:
    # Perform upgrade
    profile.role = new_role
```

### Tasks Using Role Priority

1. **`build_cohort_user`** (`breathecode/admissions/tasks.py`)
   - Called when a CohortUser is created
   - Maps CohortUser role to ProfileAcademy role
   - Upgrades profile role if needed

2. **`build_profile_academy`** (`breathecode/admissions/tasks.py`)
   - Called to create or update ProfileAcademy
   - Uses role priority to prevent downgrades

## Role Mapping

### CohortUser → ProfileAcademy

The mapping between CohortUser roles and ProfileAcademy role slugs is defined in the `CohortUser` model itself:

```python
# In breathecode/admissions/models.py
class CohortUser(models.Model):
    ROLE_TO_PROFILE_ACADEMY_SLUG = {
        TEACHER: "teacher",
        ASSISTANT: "assistant",
        REVIEWER: "homework_reviewer",
        STUDENT: "student",
    }
    
    def get_profile_academy_role_slug(self) -> str:
        """Get the ProfileAcademy role slug for this CohortUser's role."""
        return self.ROLE_TO_PROFILE_ACADEMY_SLUG.get(self.role, "student")
    
    @classmethod
    def map_role_to_profile_academy_slug(cls, cohort_user_role: str) -> str:
        """Map a CohortUser role to its ProfileAcademy role slug."""
        return cls.ROLE_TO_PROFILE_ACADEMY_SLUG.get(cohort_user_role, "student")
```

When a user is added to a cohort:

| CohortUser Role | ProfileAcademy Role | Priority |
|----------------|-------------------|----------|
| STUDENT | student | 1 |
| ASSISTANT | assistant | 2 |
| REVIEWER | homework_reviewer | 3 |
| TEACHER | teacher | 3 |

### Using the Mapping

```python
# Instance method - when you have a CohortUser instance
cohort_user = CohortUser.objects.get(id=123)
role_slug = cohort_user.get_profile_academy_role_slug()

# Class method - when you have a role string
role_slug = CohortUser.map_role_to_profile_academy_slug("TEACHER")  # Returns "teacher"
```

## Benefits

### Single Source of Truth
- Role definitions in one place
- No hardcoded priority mappings
- Easy to add new roles

### Automatic Priority
- Priority derived from inheritance
- No manual priority assignment
- Consistent across the system

### Maintainability
- Adding a new role automatically calculates its priority
- Changes to inheritance automatically update priorities
- Clear relationship between roles

## Adding New Roles

To add a new role:

1. Edit `breathecode/authenticate/role_definitions.py`
2. Add to `get_extended_roles()` function:
   ```python
   roles.append({
       "slug": "new_role",
       "name": "New Role",
       "extends": ["parent_role"],  # Optional
       "caps": extend(roles, ["parent_role"]) + [
           "additional_capability",
       ],
   })
   ```
3. Run the management command:
   ```bash
   python manage.py create_academy_roles
   ```
4. Priority is automatically calculated based on inheritance

## Testing

To verify role priorities are calculated correctly:

```python
from breathecode.authenticate.role_definitions import get_all_role_priorities

priorities = get_all_role_priorities()
print(priorities)
# {'student': 1, 'staff': 1, 'assistant': 2, 'teacher': 3, ...}
```

## Security Considerations

- Role upgrades are **one-way** (cannot downgrade automatically)
- System prevents creating duplicate ProfileAcademy records
- Role changes trigger signals for audit logging
- Priority calculation is deterministic and transparent

