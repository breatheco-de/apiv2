# Django Fixtures - Known Issues and Solutions

## Current Status

The existing Django fixtures (`dev_data.json`) have **circular dependencies** that prevent them from loading cleanly:

### The Problem

1. **Circular Dependency Chain:**
   - `admissions.CohortUser` requires `auth.User` (from authenticate fixtures)
   - `authenticate.ProfileAcademy` requires `admissions.Academy`
   - This creates a chicken-and-egg problem

2. **Signal Interference:**
   - Django signals fire during fixture loading
   - Hook managers try to access related objects before they're loaded
   - Causes `DoesNotExist` errors even with signal disabling

### What's in the Fixtures

- **admissions/dev_data.json:** Countries, cities, academies, cohorts, cohort users, syllabi
- **authenticate/dev_data.json:** Users, profiles, profile academies, roles

## Solutions

### Option 1: Use the Management Command (Partial Loading)

A management command has been created that attempts to load fixtures with signals disabled:

```bash
poetry run python manage.py load_dev_fixtures --flush
```

**Note:** This will partially load data but will skip records with dependency issues.

### Option 2: Create Minimal Test Data Programmatically (Recommended for Dev)

Instead of using fixtures, create minimal data programmatically:

```python
from breathecode.admissions.models import Country, City

# Create countries
countries = [
    ('us', 'United States'),
    ('es', 'Spain'),
    ('on', 'Online'),
]

for code, name in countries:
    Country.objects.get_or_create(code=code, defaults={'name': name})

# Create cities
cities = [
    ('Miami', 'us'),
    ('Madrid', 'es'),
    ('Remote', 'on'),
]

for city_name, country_code in cities:
    country = Country.objects.get(code=country_code)
    City.objects.get_or_create(name=city_name, defaults={'country': country})
```

### Option 3: Use Test Fixtures in Tests

For tests, use pytest fixtures (not Django fixtures) which create data on-the-fly:

```python
def test_something(database):
    country = database.create(model='admissions.Country', code='us', name='USA')
    city = database.create(model='admissions.City', name='Miami', country=country)
    # ... test logic
```

## Catalog Endpoints

New catalog endpoints have been added that don't require complex fixture data:

- **GET** `/v1/admissions/catalog/countries` - Returns all countries
- **GET** `/v1/admissions/catalog/cities` - Returns all cities  
- **GET** `/v1/admissions/catalog/timezones` - Returns all timezones

These work independently and are fully tested.

## Future Improvements

To properly fix the fixtures, they should be:

1. **Split by dependency level:**
   - `base_data.json` - Countries, cities only
   - `users.json` - Users only
   - `academies.json` - Academies, syllabi
   - `cohorts.json` - Cohorts, cohort users
   - `profiles.json` - Profile academies

2. **Loaded in order:**
   ```bash
   loaddata base_data users academies cohorts profiles
   ```

3. **Or use natural keys** instead of primary keys for foreign key references

## For Production

Production databases should be populated through:
- Migrations for base data (countries, etc.)
- Admin interface for operational data
- API endpoints for user-generated data
- Database dumps from staging/production (not fixtures)

Fixtures are primarily useful for:
- Automated testing (use pytest fixtures instead)
- Quick development setups (use simple programmatic creation)
- Documentation/examples (keep them small and focused)

