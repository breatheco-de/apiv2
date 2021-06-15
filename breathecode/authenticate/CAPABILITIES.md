# BreatheCode Capabilities

Authenticated users must belong to at least one academy with a specific role, each role has a series of capabilities that specify what any user with that role will be "capable" of doing.

Authenticated methods must be decorated with the `@capable_of` decorator in increase security validation. For example:

```python
    from breathecode.utils import capable_of
    @capable_of('crud_member')
    def post(self, request, academy_id=None):
        serializer = StaffPOSTSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Any view decorated with the @capable_of must be used passing an academy id either:

1. Anywhere on the endpoint url, E.g: `path('academy/<int:academy_id>/member', MemberView.as_view()),`
2. Or on the request header using the `Academy` header.

## Available capabilities:

This list is alive, it will grow and vary overe time:

| slug              | description                                               |
| ----------------- | --------------------------------------------------------- |
| read_members        | Allows reading the list of academy members                |
| crud_members        | Allows creating, deleting and updating academy members    |