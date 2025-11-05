# Answer Tags Feature

## Overview

Added tagging functionality to the feedback app to categorize and organize survey answers. This feature includes:

1. **AnswerTag Model** - Tagging system with priority and visibility controls
2. **Optional Fields on Answer** - syllabus, course, and tags
3. **CRUD API Endpoints** - Full tag management at `/v1/feedback/academy/tag`
4. **Admin Interface** - Manage tags through Django admin

---

## Models

### AnswerTag

A new model for categorizing answers with flexible visibility rules.

```python
class AnswerTag(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    priority = models.IntegerField(default=100)  # Lower = higher priority
    
    academy = models.ForeignKey(Academy, null=True, blank=True)
    is_private = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Visibility Rules:**
- `academy=None, is_private=False` → **Shared public tag** (available to all academies)
- `academy=X, is_private=False` → **Academy-owned public tag** (visible to that academy)
- `academy=X, is_private=True` → **Academy-owned private tag** (visible only to that academy)

### Answer Model Updates

Added three new optional fields to the `Answer` model:

```python
class Answer(models.Model):
    # ... existing fields ...
    
    # New optional categorization fields
    syllabus = models.ForeignKey("admissions.Syllabus", null=True, blank=True)
    course = models.ForeignKey(AssetCategory, null=True, blank=True)
    tags = models.ManyToManyField(AnswerTag, blank=True, related_name="answers")
```

---

## API Endpoints

All endpoints are prefixed with `/v1/feedback/academy/` and require appropriate permissions.

### 1. List Tags

**GET** `/v1/feedback/academy/tag`

**Permission:** `read_nps_answers`

**Query Parameters:**
- `academy` - Filter by ownership
  - `mine` - Only tags owned by this academy
  - `shared` - Only shared public tags (academy=null)
- `sort` - Sort field (default: `priority`)

**Returns:** Array of tags accessible to the academy (owned + public shared)

**Example:**
```bash
GET /v1/feedback/academy/tag?academy=mine&sort=priority
Authorization: Token abc123
Academy: 1

# Response:
[
  {
    "id": 1,
    "slug": "technical-issue",
    "title": "Technical Issue",
    "description": "Problems with platform or tools",
    "priority": 10,
    "is_private": false,
    "academy": {
      "id": 1,
      "slug": "miami",
      "name": "Miami Academy"
    },
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "slug": "positive-feedback",
    "title": "Positive Feedback",
    "description": "General positive comments",
    "priority": 20,
    "is_private": false,
    "academy": null,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

### 2. Get Single Tag

**GET** `/v1/feedback/academy/tag/<tag_id>`

**Permission:** `read_nps_answers`

**Returns:** Single tag details

**Example:**
```bash
GET /v1/feedback/academy/tag/1
Authorization: Token abc123
Academy: 1

# Response:
{
  "id": 1,
  "slug": "technical-issue",
  "title": "Technical Issue",
  "description": "Problems with platform or tools",
  "priority": 10,
  "is_private": false,
  "academy": {
    "id": 1,
    "slug": "miami",
    "name": "Miami Academy"
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### 3. Create Tag

**POST** `/v1/feedback/academy/tag`

**Permission:** `crud_survey`

**Payload:**
```json
{
  "slug": "technical-issue",
  "title": "Technical Issue",
  "description": "Problems with platform or tools",
  "priority": 10,
  "is_private": false,
  "academy": 1  // Optional - defaults to current academy if not provided
}
```

**Validation Rules:**
- If `is_private=true`, `academy` must be set
- If `academy=null` and `is_private=false`, creates a shared public tag
- `slug` must be unique across all tags

**Example:**
```bash
POST /v1/feedback/academy/tag
Authorization: Token abc123
Academy: 1
Content-Type: application/json

{
  "slug": "content-quality",
  "title": "Content Quality",
  "description": "Feedback about course content and materials",
  "priority": 15,
  "is_private": false
}

# Response: 201 CREATED
{
  "id": 3,
  "slug": "content-quality",
  "title": "Content Quality",
  "description": "Feedback about course content and materials",
  "priority": 15,
  "is_private": false,
  "academy": {
    "id": 1,
    "slug": "miami",
    "name": "Miami Academy"
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Create Shared Public Tag:**
```json
{
  "slug": "graduation-ready",
  "title": "Graduation Ready",
  "description": "Student is ready to graduate",
  "priority": 5,
  "is_private": false,
  "academy": null  // Shared across all academies
}
```

### 4. Update Tag

**PUT** `/v1/feedback/academy/tag/<tag_id>`

**Permission:** `crud_survey`

**Restrictions:**
- Can only update tags owned by the academy
- Cannot change `slug`

**Payload:**
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "priority": 20,
  "is_private": false
}
```

**Example:**
```bash
PUT /v1/feedback/academy/tag/1
Authorization: Token abc123
Academy: 1
Content-Type: application/json

{
  "priority": 5,
  "description": "Updated description for technical issues"
}

# Response: 200 OK
{
  "id": 1,
  "slug": "technical-issue",  // slug cannot be changed
  "title": "Technical Issue",
  "description": "Updated description for technical issues",
  "priority": 5,
  "is_private": false,
  "academy": {
    "id": 1,
    "slug": "miami",
    "name": "Miami Academy"
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-02T00:00:00Z"
}
```

### 5. Delete Tag

**DELETE** `/v1/feedback/academy/tag/<tag_id>`

**Permission:** `crud_survey`

**Restrictions:**
- Can only delete tags owned by the academy
- Supports single delete by ID

**Example:**
```bash
DELETE /v1/feedback/academy/tag/1
Authorization: Token abc123
Academy: 1

# Response: 204 NO CONTENT
```

**Bulk Delete:**
```bash
DELETE /v1/feedback/academy/tag?id=1,2,3
Authorization: Token abc123
Academy: 1

# Response: 204 NO CONTENT
```

---

## Usage Examples

### Example 1: Create Academy-Specific Tags

```bash
# Create "mentor-feedback" tag for Miami academy
POST /v1/feedback/academy/tag
Academy: 1

{
  "slug": "mentor-feedback",
  "title": "Mentor Feedback",
  "description": "Feedback about mentor performance",
  "priority": 10,
  "is_private": false
}

# Create "internal-review" private tag
POST /v1/feedback/academy/tag
Academy: 1

{
  "slug": "internal-review",
  "title": "Internal Review",
  "description": "For internal staff review only",
  "priority": 100,
  "is_private": true
}
```

### Example 2: Create Shared Tags (Available to All Academies)

```bash
# Only superadmins or authorized users can create shared tags
POST /v1/feedback/academy/tag
Academy: 1

{
  "slug": "excellent-experience",
  "title": "Excellent Experience",
  "description": "Student had an excellent overall experience",
  "priority": 1,
  "is_private": false,
  "academy": null  // Makes it shared
}
```

### Example 3: Filter and Sort Tags

```bash
# Get only academy-owned tags, sorted by priority
GET /v1/feedback/academy/tag?academy=mine&sort=priority

# Get only shared public tags
GET /v1/feedback/academy/tag?academy=shared

# Get all accessible tags (default)
GET /v1/feedback/academy/tag
```

### Example 4: Tag an Answer

When creating or updating answers, you can now include tags, syllabus, and course:

```python
from breathecode.feedback.models import Answer, AnswerTag
from breathecode.admissions.models import Syllabus
from breathecode.registry.models import AssetCategory

answer = Answer.objects.create(
    user=user,
    cohort=cohort,
    academy=academy,
    title="How was your experience?",
    score=9,
    comment="Great experience with some minor issues",
    # New optional fields
    syllabus=Syllabus.objects.get(slug='full-stack'),
    course=AssetCategory.objects.get(slug='python')
)

# Add tags
answer.tags.add(
    AnswerTag.objects.get(slug='positive-feedback'),
    AnswerTag.objects.get(slug='technical-issue')
)
```

### Example 5: Query Answers by Tags

```python
# Get all answers with "technical-issue" tag
technical_issues = Answer.objects.filter(tags__slug='technical-issue')

# Get answers with multiple tags
priority_issues = Answer.objects.filter(
    tags__slug__in=['technical-issue', 'urgent']
).distinct()

# Get answers by syllabus
python_answers = Answer.objects.filter(
    syllabus__slug='full-stack',
    course__slug='python'
)
```

---

## Admin Interface

### Managing Tags

1. Navigate to **Django Admin** → **Feedback** → **Answer Tags**
2. Features:
   - List view shows: slug, title, priority, academy, is_private, created_at
   - Filter by: is_private, academy
   - Search by: slug, title, description
   - Default ordering: priority (ascending), then title

### Creating Tags in Admin

**Academy-Owned Tag:**
```
Slug: platform-bug
Title: Platform Bug
Description: Technical issues with the learning platform
Priority: 5
Academy: Miami Academy
Is Private: No
```

**Shared Public Tag:**
```
Slug: needs-follow-up
Title: Needs Follow-up
Description: Requires staff follow-up action
Priority: 1
Academy: (leave empty)
Is Private: No
```

**Private Tag:**
```
Slug: internal-alert
Title: Internal Alert
Description: For internal staff only
Priority: 1
Academy: Miami Academy
Is Private: Yes
```

---

## Database Schema

### Migration Created

File: `breathecode/feedback/migrations/0004_add_answer_tags_and_optional_fields.py`

**Changes:**
1. Create `AnswerTag` table
2. Add `syllabus_id` foreign key to `Answer` table
3. Add `course_id` foreign key to `Answer` table
4. Create many-to-many relationship table `answer_tags` linking `Answer` and `AnswerTag`

**To apply migration:**
```bash
poetry run python manage.py migrate feedback
```

---

## Tag Priority Guidelines

**Recommended Priority Values:**

- **1-10:** Critical/urgent tags (needs-immediate-attention, blocker-issue)
- **11-20:** Important feedback (mentor-feedback, content-quality)
- **21-50:** General categories (technical-issue, positive-feedback)
- **51-100:** Low priority or administrative (archived, internal-notes)

Lower numbers appear first in lists.

---

## Security & Permissions

### Required Permissions

- **Read Tags:** `read_nps_answers`
- **Create/Update/Delete Tags:** `crud_survey`

### Access Control

1. **Academy Isolation:** 
   - Academy can only CREATE/UPDATE/DELETE its own tags
   - Academy can READ its own tags + public shared tags

2. **Shared Tags:**
   - Only tags with `academy=null` and `is_private=false` are shared
   - Visible to all academies when listing

3. **Private Tags:**
   - Must have an academy assigned
   - Only visible to that specific academy

---

## Testing

### Example Test Cases

```python
# Test 1: Create academy-owned tag
def test_create_academy_tag():
    response = self.client.post(
        '/v1/feedback/academy/tag',
        {
            'slug': 'test-tag',
            'title': 'Test Tag',
            'priority': 10,
            'is_private': False
        },
        HTTP_ACADEMY=1
    )
    assert response.status_code == 201

# Test 2: Validate private tag requires academy
def test_private_tag_needs_academy():
    response = self.client.post(
        '/v1/feedback/academy/tag',
        {
            'slug': 'test-tag',
            'title': 'Test Tag',
            'is_private': True,
            'academy': None  # Should fail
        },
        HTTP_ACADEMY=1
    )
    assert response.status_code == 400

# Test 3: List includes academy tags and shared tags
def test_list_includes_shared_tags():
    # Create shared tag
    AnswerTag.objects.create(
        slug='shared-tag',
        title='Shared Tag',
        academy=None,
        is_private=False
    )
    
    response = self.client.get(
        '/v1/feedback/academy/tag',
        HTTP_ACADEMY=1
    )
    
    assert len(response.data) >= 1

# Test 4: Cannot update another academy's tags
def test_cannot_update_other_academy_tags():
    tag = AnswerTag.objects.create(
        slug='other-tag',
        title='Other Tag',
        academy=other_academy
    )
    
    response = self.client.put(
        f'/v1/feedback/academy/tag/{tag.id}',
        {'priority': 5},
        HTTP_ACADEMY=1
    )
    
    assert response.status_code == 404
```

---

## Best Practices

### Tag Naming

1. **Use descriptive slugs:** `technical-issue` not `issue1`
2. **Be consistent:** Follow a naming convention across academies
3. **Avoid abbreviations:** `mentor-feedback` not `mtr-fdbk`

### Tag Management

1. **Use priority wisely:** Reserve low numbers (1-10) for critical tags
2. **Share common tags:** Create shared tags for common categories
3. **Document purposes:** Use descriptions to clarify tag usage
4. **Regular cleanup:** Archive or delete unused tags

### Tagging Answers

1. **Use multiple tags:** Answers can have multiple relevant tags
2. **Combine with filters:** Use tags + syllabus + course for detailed reporting
3. **Tag consistently:** Establish guidelines for when to apply specific tags

---

## Migration Guide

### Existing Answers

All existing answers will have:
- `syllabus=null`
- `course=null`
- `tags=[]` (empty)

These fields are optional and can be populated retroactively if needed.

### Backwards Compatibility

✅ **Fully backwards compatible:**
- All new fields are optional (nullable)
- Existing code continues to work
- No breaking changes to API or serializers

---

## Troubleshooting

### Issue: Cannot create shared tag

**Error:** "Private tags must have an academy assigned"

**Solution:** Ensure `is_private=False` when creating shared tags with `academy=null`

```json
{
  "academy": null,
  "is_private": false  // Must be false for shared tags
}
```

### Issue: Tag not visible to academy

**Check:**
1. Is the tag `is_private=True` and owned by another academy?
2. Is the tag owned by another academy with `is_private=False`? (Not shared)

**Solution:** Shared tags must have `academy=null`, not just `is_private=False`

### Issue: Cannot update shared tag

**Explanation:** Only the owning academy (or superadmin) can update tags.

**Solution:** Contact the tag owner or create your own academy-specific tag.

---

## Summary

The Answer Tags feature provides a flexible, powerful system for categorizing feedback with:

✅ **Academy isolation** - Each academy manages its own tags
✅ **Shared resources** - Common tags available to all academies  
✅ **Priority sorting** - Organize tags by importance
✅ **Optional enrichment** - Add syllabus, course, and tags to answers
✅ **Full CRUD API** - Complete tag management via REST endpoints
✅ **Admin interface** - Easy management through Django admin

This enables better organization, reporting, and analysis of student feedback across the platform.

