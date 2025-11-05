# Feedback App - Tags Feature Changelog

## Version 2.0 - FeedbackTags Feature

### Added

#### Models
- **FeedbackTag Model** - New model for categorizing feedback (answers and reviews)
  - `slug` - Unique identifier
  - `title` - Display name
  - `description` - Optional description
  - `priority` - Sorting priority (lower = higher priority)
  - `academy` - Academy ownership (null for shared tags)
  - `is_private` - Visibility control
- **Answer Model Updates**
  - Added `syllabus` field (ForeignKey to Syllabus)
  - Added `course_slug` field (CharField - references marketing.Course model)
  - Added `tags` field (ManyToMany to FeedbackTag)
- **Review Model Updates**
  - Added `syllabus` field (ForeignKey to Syllabus)
  - Added `course_slug` field (CharField - references marketing.Course model)
  - Added `tags` field (ManyToMany to FeedbackTag)

#### API Endpoints
- `GET /v1/feedback/academy/tag` - List feedback tags
- `GET /v1/feedback/academy/tag/<tag_id>` - Get single tag
- `POST /v1/feedback/academy/tag` - Create new tag
- `PUT /v1/feedback/academy/tag/<tag_id>` - Update tag
- `DELETE /v1/feedback/academy/tag/<tag_id>` - Delete tag

#### Admin Interface
- New admin page for FeedbackTag model
- List display: slug, title, priority, academy, is_private, created_at
- Filters: is_private, academy
- Search: slug, title, description

#### Management Commands
- **backfill_feedback_syllabus** - Backfill syllabus field on existing Answer and Review records based on their cohort's syllabus_version

### Changed

#### Model Naming
- Renamed `AnswerTag` to `FeedbackTag` throughout the codebase
- Updated all references, serializers, views, and admin registrations
- Migration: `0004_add_feedback_tags_and_optional_fields.py`

### Migration Notes

To apply this update:

```bash
poetry run python manage.py migrate feedback
```

This migration will:
1. Create the `FeedbackTag` model
2. Add `syllabus`, `course_slug`, and `tags` fields to `Answer` model
3. Add `syllabus`, `course_slug`, and `tags` fields to `Review` model
4. Create many-to-many relationship tables

### Backwards Compatibility

✅ **Fully backwards compatible**
- All new fields are optional (nullable)
- Existing data remains unchanged
- No breaking changes to existing API endpoints
- Existing serializers work without modification

#### Backfilling Existing Data

For existing Answer and Review records, you can backfill the `syllabus` field based on their cohort's syllabus:

```bash
# Dry run to see what would be updated
poetry run python manage.py backfill_feedback_syllabus --dry-run

# Update all records
poetry run python manage.py backfill_feedback_syllabus

# Update only Answer records
poetry run python manage.py backfill_feedback_syllabus --model answer

# Update only Review records
poetry run python manage.py backfill_feedback_syllabus --model review

# Limit the number of records processed
poetry run python manage.py backfill_feedback_syllabus --limit 100
```

This command will:
- Find all Answer/Review records with a cohort but no syllabus
- Set `syllabus = cohort.syllabus_version.syllabus`
- Skip records where cohort has no syllabus_version
- Provide detailed output of what was updated

### Usage

#### Create Tags
```bash
POST /v1/feedback/academy/tag
{
  "slug": "positive-feedback",
  "title": "Positive Feedback",
  "description": "General positive comments",
  "priority": 10,
  "is_private": false
}
```

#### Tag Answers or Reviews
```python
# Add tags
answer.tags.add(FeedbackTag.objects.get(slug='positive-feedback'))
review.tags.add(FeedbackTag.objects.get(slug='needs-follow-up'))

# Set course_slug (references marketing.Course)
answer.course_slug = 'full-stack-web-development'
answer.save()

review.course_slug = 'data-science-bootcamp'
review.save()
```

### Permissions

- **Read Tags**: `read_nps_answers`
- **Manage Tags**: `crud_survey`

### Tag Visibility Rules

1. **Shared Public Tags** (`academy=null, is_private=false`)
   - Available to all academies
   - Created by platform admins

2. **Academy Public Tags** (`academy=X, is_private=false`)
   - Visible to that academy
   - Can be created by academy staff

3. **Academy Private Tags** (`academy=X, is_private=true`)
   - Only visible to that academy
   - Requires academy assignment

