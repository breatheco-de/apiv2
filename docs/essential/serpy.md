# Serpy

Serpy in which it is:

- Faster [serializer](./django-rest-framework/serializers.md).
- Easy to use.
- It includes custom fields.
- It includes dynamic field resolution.

It is weak in:

- Telling Django which fields include and which do not on the [ORM](./django/models.md).

## When uses Serpy?

When you need to serialize and GET request.

## When does not use Serpy?

When you need the serialize to create or update a [row](<https://en.wikipedia.org/wiki/Row_(database)>) in the [database](https://en.wikipedia.org/wiki/Database), it is in the POST and PUT methods, you must use [DRF Serializer](./django-rest-framework/serializers.md) instead.

## fields

Read [this](https://serpy.readthedocs.io/en/latest/api.html#fields).

## Custom fields

Read [this](https://serpy.readthedocs.io/en/latest/custom-fields.html).

## Related articles

- [HTTP](https://en.wikipedia.org/wiki/HTTP).
- [REST](https://en.wikipedia.org/wiki/REST).
