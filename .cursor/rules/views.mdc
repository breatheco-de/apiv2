---
description:
globs: breathecode/*/views.py
alwaysApply: false
---
# About the APIViews

## View Class Type

**Always use `APIView` from `rest_framework.views`, never use `ViewSet`.**

### Why APIView?

- Consistency: The entire codebase uses `APIView` for manual URL routing
- Simplicity: No need for dictionary mapping syntax in URLs
- Clarity: Each endpoint pattern gets its own view class, making the code more explicit

### ViewSet is Forbidden

❌ **DO NOT USE:**
```py
from adrf.viewsets import ViewSet

class MyView(ViewSet):
    def get(self, request):
        ...
```

✅ **USE INSTEAD:**
```py
from rest_framework.views import APIView

class MyView(APIView):
    def get(self, request):
        ...
```

### Multiple Endpoint Patterns

When you need different endpoints (list, by_id, by_slug), create separate view classes:

```py
# List and create
class JobFamilyView(APIView, GenerateLookupsMixin):
    def get(self, request, academy_id=None):
        # List all items
        ...
    
    def post(self, request, academy_id=None):
        # Create new item
        ...

# By ID operations
class JobFamilyByIdView(APIView):
    def get(self, request, job_family_id=None, academy_id=None):
        # Get by ID
        ...
    
    def put(self, request, job_family_id=None, academy_id=None):
        # Update by ID
        ...
    
    def delete(self, request, job_family_id=None, academy_id=None):
        # Delete by ID
        ...

# By slug operations
class JobFamilyBySlugView(APIView):
    def get(self, request, job_family_slug=None, academy_id=None):
        # Get by slug
        ...
    
    def put(self, request, job_family_slug=None, academy_id=None):
        # Update by slug
        ...
    
    def delete(self, request, job_family_slug=None, academy_id=None):
        # Delete by slug
        ...
```

### URL Patterns

Use the standard `.as_view()` pattern without dictionary mapping:

```py
# ✅ CORRECT
urlpatterns = [
    path("job/family", JobFamilyView.as_view(), name="job_family"),
    path("job/family/<int:job_family_id>", JobFamilyByIdView.as_view(), name="job_family_id"),
    path("job/family/<str:job_family_slug>", JobFamilyBySlugView.as_view(), name="job_family_slug"),
]

# ❌ WRONG - Dictionary mapping syntax is only used in legacy media app
urlpatterns = [
    path("job/family", JobFamilyView.as_view({"get": "get", "post": "post"}), name="job_family"),
]
```

## Making Endpoints Private

There are two ways to approaches to make endpoints private:

### Capable Of

If the endpoint has "/academy/" it will probably be called by an academy staff member and you can use [capable_of.py](mdc:breathecode/utils/decorators/capable_of.py) decorator to make sure it has a particular role like this:

```py
    @capable_of("task_delivery_details")
    def get(self, request, task_id, academy_id):
```

The capable_of decorator will always make sure the academy_id is retrieved from the request header and passed to the view methods.

The list of possible capabilities is hardcoded at [create_academy_roles.py](mdc:breathecode/authenticate/management/commands/create_academy_roles.py)

### Has Permission

Or if the endpoint is not for an academy, you can use the [has_permission.py](mdc:breathecode/utils/decorators/has_permission.py) decorator like this:

```py
    @has_permission('superadmin')
    def get(self, request, asset_slug=None):
```

These permissions are django permissions assigned to groups or users and they are hardcoded in [set_permissions.py](mdc:breathecode/authenticate/management/commands/set_permissions.py)
