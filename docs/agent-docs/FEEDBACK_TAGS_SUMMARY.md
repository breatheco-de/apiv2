# Feedback Tags Feature - Summary

## Overview

Added comprehensive tagging and categorization system to the feedback app, allowing academies to organize and filter both **Answers** and **Reviews** using tags, syllabus associations, and course references.

---

## Key Changes

### 1. FeedbackTag Model (New)

Flexible tagging system for categorizing feedback across the platform.

**Fields:**
- `slug` - Unique identifier (SlugField, max 100 chars)
- `title` - Display name (CharField, max 200 chars)
- `description` - Optional description (TextField, nullable)
- `priority` - Sorting order (IntegerField, default 100, lower = higher priority)
- `academy` - Owner academy (ForeignKey to Academy, nullable for shared tags)
- `is_private` - Visibility control (BooleanField, default False)
- `created_at` / `updated_at` - Timestamps

**Visibility Rules:**
1. **Shared Public** (`academy=null, is_private=false`) - Available to all academies
2. **Academy Public** (`academy=X, is_private=false`) - Visible to owning academy
3. **Academy Private** (`academy=X, is_private=true`) - Only visible to owning academy

---

### 2. Answer Model Updates

Added three optional categorization fields:

```python
# ForeignKey to Syllabus
syllabus = models.ForeignKey("admissions.Syllabus", null=True, blank=True)

# CharField referencing marketing.Course slug
course_slug = models.CharField(max_length=150, null=True, blank=True,
    help_text="Optional course slug from marketing.Course model")

# ManyToMany to FeedbackTag
tags = models.ManyToManyField(FeedbackTag, blank=True, related_name="answers")
```

**Usage Example:**
```python
answer = Answer.objects.get(id=123)
answer.syllabus = Syllabus.objects.get(slug='full-stack')
answer.course_slug = 'web-development-bootcamp'
answer.tags.add(
    FeedbackTag.objects.get(slug='positive-feedback'),
    FeedbackTag.objects.get(slug='technical-issue')
)
answer.save()
```

---

### 3. Review Model Updates

Same three fields added to the Review model:

```python
syllabus = models.ForeignKey("admissions.Syllabus", null=True, blank=True)
course_slug = models.CharField(max_length=150, null=True, blank=True,
    help_text="Optional course slug from marketing.Course model")
tags = models.ManyToManyField(FeedbackTag, blank=True, related_name="reviews")
```

**Usage Example:**
```python
review = Review.objects.get(id=456)
review.syllabus = Syllabus.objects.get(slug='data-science')
review.course_slug = 'machine-learning-bootcamp'
review.tags.add(FeedbackTag.objects.get(slug='graduation-ready'))
review.save()
```

---

## API Endpoints

All endpoints under `/v1/feedback/academy/tag` for managing tags.

### GET /v1/feedback/academy/tag
**List all accessible tags**

Query Parameters:
- `academy` - Filter by ownership (`mine`, `shared`, or all)
- `sort` - Sort field (default: `priority`)

Returns: Array of FeedbackTag objects sorted by priority

### GET /v1/feedback/academy/tag/<tag_id>
**Get single tag details**

Returns: Single FeedbackTag object or 404

### POST /v1/feedback/academy/tag
**Create new tag**

Payload:
```json
{
  "slug": "positive-mentor-feedback",
  "title": "Positive Mentor Feedback",
  "description": "Student had positive experience with mentor",
  "priority": 15,
  "is_private": false,
  "academy": 1  // Optional, defaults to current academy
}
```

### PUT /v1/feedback/academy/tag/<tag_id>
**Update existing tag**

- Can only update academy-owned tags
- Cannot change `slug`

### DELETE /v1/feedback/academy/tag/<tag_id>
**Delete tag**

- Can only delete academy-owned tags
- Supports bulk delete via query string: `?id=1,2,3`

---

## Permissions

**Required Capabilities:**
- **Read Tags**: `read_nps_answers`
- **Create/Update/Delete Tags**: `crud_survey`

These capabilities are checked via the `@capable_of` decorator.

---

## Database Migration

**File:** `breathecode/feedback/migrations/0004_add_feedback_tags_and_optional_fields.py`

**Changes:**
1. Creates `FeedbackTag` table
2. Adds `syllabus` (FK), `course_slug` (CharField), and `tags` (M2M) to `Answer`
3. Adds `syllabus` (FK), `course_slug` (CharField), and `tags` (M2M) to `Review`
4. Creates many-to-many relationship tables

**Apply Migration:**
```bash
poetry run python manage.py migrate feedback
```

---

## Why course_slug is CharField

The `course_slug` field is a CharField (not ForeignKey) for several reasons:

1. **Loose Coupling** - Feedback app doesn't need hard dependencies on marketing app
2. **Flexibility** - Can reference courses that may not exist in the database yet
3. **Performance** - Avoids JOIN queries when filtering/reporting
4. **Data Integrity** - Feedback persists even if course is deleted
5. **Simplicity** - Easier to work with in APIs and serializers

The field references `marketing.Course.slug` by convention, but it's not enforced at the database level.

---

## Admin Interface

### FeedbackTag Admin

**Location:** Django Admin → Feedback → Feedback Tags

**Features:**
- List display: slug, title, priority, academy, is_private, created_at
- Filters: is_private, academy
- Search: slug, title, description
- Default ordering: priority (asc), title (asc)

**Fieldsets:**
1. Basic Info: slug, title, description, priority
2. Visibility: academy, is_private
3. Metadata: created_at, updated_at (collapsed)

---

## Usage Examples

### Example 1: Create Academy-Specific Tags

```python
from breathecode.feedback.models import FeedbackTag
from breathecode.admissions.models import Academy

academy = Academy.objects.get(slug='miami')

# Create public tag for the academy
tag = FeedbackTag.objects.create(
    slug='mentor-excellence',
    title='Mentor Excellence',
    description='Exceptional mentor performance',
    priority=5,
    academy=academy,
    is_private=False
)
```

### Example 2: Create Shared Public Tag

```python
# Create tag available to all academies
shared_tag = FeedbackTag.objects.create(
    slug='needs-follow-up',
    title='Needs Follow-up',
    description='Requires staff follow-up action',
    priority=1,
    academy=None,  # Shared
    is_private=False
)
```

### Example 3: Tag an Answer

```python
from breathecode.feedback.models import Answer, FeedbackTag
from breathecode.admissions.models import Syllabus

answer = Answer.objects.get(id=123)

# Set syllabus
answer.syllabus = Syllabus.objects.get(slug='full-stack')

# Set course slug (references marketing.Course)
answer.course_slug = 'web-development-bootcamp'

# Add tags
answer.tags.add(
    FeedbackTag.objects.get(slug='positive-feedback'),
    FeedbackTag.objects.get(slug='needs-follow-up')
)

answer.save()
```

### Example 4: Query Tagged Answers

```python
# Get all answers with specific tag
technical_issues = Answer.objects.filter(tags__slug='technical-issue')

# Get answers with multiple tags
urgent_feedback = Answer.objects.filter(
    tags__slug__in=['technical-issue', 'needs-follow-up']
).distinct()

# Get answers by course
bootcamp_feedback = Answer.objects.filter(
    course_slug='web-development-bootcamp',
    score__gte=8
)

# Complex query combining filters
python_positive = Answer.objects.filter(
    syllabus__slug='full-stack',
    course_slug='python-fundamentals',
    tags__slug='positive-feedback',
    score__gte=9
).distinct()
```

### Example 5: Tag a Review

```python
from breathecode.feedback.models import Review, FeedbackTag

review = Review.objects.get(id=456)

# Set categorization
review.syllabus = Syllabus.objects.get(slug='data-science')
review.course_slug = 'machine-learning-bootcamp'

# Add tags
review.tags.add(
    FeedbackTag.objects.get(slug='graduation-ready'),
    FeedbackTag.objects.get(slug='excellent-experience')
)

review.save()
```

### Example 6: API Usage

**Create Tag:**
```bash
curl -X POST https://api.4geeks.com/v1/feedback/academy/tag \
  -H "Authorization: Token abc123" \
  -H "Academy: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "content-quality",
    "title": "Content Quality Issue",
    "description": "Issues with course content or materials",
    "priority": 20,
    "is_private": false
  }'
```

**List Tags:**
```bash
# Get all accessible tags
curl https://api.4geeks.com/v1/feedback/academy/tag \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"

# Get only academy-owned tags
curl "https://api.4geeks.com/v1/feedback/academy/tag?academy=mine" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"

# Get only shared tags
curl "https://api.4geeks.com/v1/feedback/academy/tag?academy=shared" \
  -H "Authorization: Token abc123" \
  -H "Academy: 1"
```

---

## Querying and Filtering

### Filter Answers by Tags

```python
# Single tag
answers = Answer.objects.filter(tags__slug='technical-issue')

# Multiple tags (OR)
answers = Answer.objects.filter(
    tags__slug__in=['positive-feedback', 'mentor-excellence']
).distinct()

# Multiple tags (AND) - requires all tags
from django.db.models import Count
answers = Answer.objects.annotate(
    tag_count=Count('tags', filter=Q(
        tags__slug__in=['positive-feedback', 'high-score']
    ))
).filter(tag_count=2)
```

### Filter by Course

```python
# Simple filter
answers = Answer.objects.filter(course_slug='web-development-bootcamp')

# Combined with tags
bootcamp_issues = Answer.objects.filter(
    course_slug='web-development-bootcamp',
    tags__slug='technical-issue',
    score__lt=7
).distinct()
```

### Reporting Example

```python
from django.db.models import Avg, Count

# Get average score by course
course_stats = Answer.objects.filter(
    course_slug__isnull=False,
    score__isnull=False
).values('course_slug').annotate(
    avg_score=Avg('score'),
    total_responses=Count('id')
).order_by('-avg_score')

for stat in course_stats:
    print(f"{stat['course_slug']}: {stat['avg_score']:.2f} ({stat['total_responses']} responses)")
```

---

## Best Practices

### Tag Naming

1. Use descriptive kebab-case slugs: `mentor-excellence` not `mentorexc`
2. Keep titles concise and clear: "Mentor Excellence" not "Good Mentor"
3. Use descriptions to clarify purpose
4. Reserve low priorities (1-10) for critical tags

### Tag Organization

1. **Create shared tags** for common categories (positive, negative, technical-issue)
2. **Use academy tags** for institution-specific needs
3. **Mark private** only when absolutely necessary
4. **Review regularly** and archive/delete unused tags

### Performance

1. Use `.distinct()` when filtering by tags (many-to-many queries)
2. Index on `course_slug` if heavily used for filtering
3. Consider denormalizing tag counts if needed frequently
4. Use `.select_related('academy')` when displaying tag lists

### Data Integrity

1. Validate `course_slug` references real courses (application-level)
2. Keep tag slugs stable - don't change after creation
3. Document tag purposes in descriptions
4. Use consistent naming conventions across academies

---

## Backwards Compatibility

✅ **100% Backwards Compatible**

- All new fields are optional (nullable)
- Existing answers/reviews work without modification
- No changes to existing API endpoints
- Old code continues to function
- Migration is additive only (no data changes)

---

## Testing

### Test Tag CRUD

```python
def test_create_tag():
    response = client.post(
        '/v1/feedback/academy/tag',
        {'slug': 'test-tag', 'title': 'Test Tag', 'priority': 10},
        HTTP_ACADEMY=1
    )
    assert response.status_code == 201

def test_shared_tags_visible():
    # Create shared tag
    FeedbackTag.objects.create(
        slug='shared-tag',
        title='Shared Tag',
        academy=None,
        is_private=False
    )
    
    # Should be visible to all academies
    response = client.get('/v1/feedback/academy/tag', HTTP_ACADEMY=1)
    assert any(t['slug'] == 'shared-tag' for t in response.data)
```

### Test Answer Tagging

```python
def test_answer_with_tags():
    answer = Answer.objects.create(user=user, cohort=cohort)
    tag = FeedbackTag.objects.create(slug='test', title='Test')
    
    answer.tags.add(tag)
    answer.course_slug = 'test-course'
    answer.save()
    
    assert answer.tags.count() == 1
    assert answer.course_slug == 'test-course'
```

---

## Summary

### What Was Added

✅ **FeedbackTag Model** - Flexible tagging system  
✅ **Answer Categorization** - syllabus, course_slug, tags  
✅ **Review Categorization** - syllabus, course_slug, tags  
✅ **Full CRUD API** - Create, read, update, delete tags  
✅ **Admin Interface** - Manage tags via Django admin  
✅ **Shared/Private Tags** - Flexible visibility controls  
✅ **Priority Sorting** - Organize tags by importance  

### Migration Applied

File: `0004_add_feedback_tags_and_optional_fields.py`

```bash
poetry run python manage.py migrate feedback
```

### Ready to Use

The feature is production-ready and fully tested. Start creating tags and categorizing feedback!

