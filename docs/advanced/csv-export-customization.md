# CSV Export Customization

## Overview

The CSV export system now supports customizable field selection with labels, dot notation for related fields, and calculated properties/methods.

## How It Works

### 1. Define CSV Fields in Your Model

Add a static method `get_csv_fields()` to your model that returns a list of tuples:

```python
class EventCheckin(models.Model):
    # ... fields ...
    
    @staticmethod
    def get_csv_fields():
        """
        Define custom fields for CSV export with user-friendly labels.
        Returns a list of tuples: (header_name, field_path)
        """
        return [
            ('ID', 'id'),                              # Simple field
            ('Email', 'email'),                        # Simple field
            ('Event Title', 'event.title'),            # Related field (dot notation)
            ('Academy', 'event.academy.name'),         # Deep relation (dot notation)
            ('Attendee Name', 'attendee_name'),        # Calculated property
        ]
    
    @property
    def attendee_name(self):
        """Calculated field example"""
        if self.attendee:
            return f"{self.attendee.first_name} {self.attendee.last_name}".strip()
        return ''
```

### 2. Field Types Supported

#### Simple Fields
```python
('Email', 'email')  # Direct model field
```

#### Related Fields with Dot Notation
```python
('Event Title', 'event.title')              # One level deep
('Academy', 'event.academy.name')           # Multiple levels deep
('Attendee First Name', 'attendee.first_name')
```

#### Calculated Properties
```python
('Attendee Name', 'attendee_name')  # References @property attendee_name

@property
def attendee_name(self):
    if self.attendee:
        return f"{self.attendee.first_name} {self.attendee.last_name}".strip()
    return ''
```

#### Methods (without @property)
```python
('Status Text', 'get_status_display')  # Django's built-in method

def custom_method(self):
    return "calculated value"
```

### 3. CSV Output

The exported CSV will have:
- **Custom column headers** (first item in tuple)
- **Related data** resolved via dot notation
- **Calculated values** from properties/methods
- **Null-safe** handling (returns empty string for None values)

Example output:
```csv
ID,Email,Attendee First Name,Attendee Last Name,Attendee Name,Event ID,Event Slug,Event Title,Academy,Status,Created At,Attended At,UTM Source,UTM Medium,UTM Campaign
1,john@example.com,John,Doe,John Doe,42,python-workshop,Python Workshop,Miami Campus,DONE,2024-01-15 10:30:00,2024-01-15 11:00:00,google,cpc,workshop
```

## Benefits

- ✅ **Custom Labels**: User-friendly column names
- ✅ **Related Data**: Access foreign key fields without joins
- ✅ **Calculated Fields**: Include computed values
- ✅ **Flexible**: Mix simple, related, and calculated fields
- ✅ **Backward Compatible**: Falls back to all model fields if not defined
- ✅ **Clean Code**: Everything in the model, no separate serializers needed

## Implementation Details

### File Updates

1. **`breathecode/monitoring/actions.py`**
   - Enhanced `download_csv()` function
   - Supports tuple format `(header, field_path)`
   - Handles dot notation for related fields
   - Calls properties/methods for calculated fields

2. **`breathecode/events/models.py`**
   - Added `get_csv_fields()` to `EventCheckin` model
   - Added `attendee_name` property as example calculated field

## Example: EventCheckin CSV Export

When you export EventCheckin records via:
```
GET /v1/events/academy/{academy_id}/checkin.csv
```

The system will:
1. Check if `EventCheckin.get_csv_fields()` exists
2. Use custom field definitions with labels
3. Resolve related fields (event.slug, event.academy.name, etc.)
4. Calculate properties (attendee_name)
5. Export to CSV with clean headers

## Adding to Other Models

To enable custom CSV export for any model:

```python
class MyModel(models.Model):
    # ... fields ...
    
    @staticmethod
    def get_csv_fields():
        return [
            ('Custom Header', 'field_name'),
            ('Related Field', 'foreign_key.field'),
            ('Calculated', 'my_property'),
        ]
    
    @property
    def my_property(self):
        # Your calculation logic
        return calculated_value
```

That's it! The CSV export will automatically use your custom configuration.

