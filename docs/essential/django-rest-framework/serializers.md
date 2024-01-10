# Serializers

A serializer is an element (a [class](<https://en.wikipedia.org/wiki/Class_(computer_programming)>) this case) that translates and [object](<https://en.wikipedia.org/wiki/Object_(computer_science)>) ([Object-oriented programming](https://en.wikipedia.org/wiki/Object-oriented_programming)) and generate an output that should be useful by something, in Django a serializer is used to format the object before be sent. We just using the [Django Rest Framework](https://www.django-rest-framework.org) Serializers for POST and PUT methods, for the GET method we are using [Serpy](../serpy/introduction) because it is faster than DRF Serializers.

Related articles:

- [HTTP](https://en.wikipedia.org/wiki/HTTP).
- [REST](https://en.wikipedia.org/wiki/REST).

## Writing Serializers

Read [this](https://www.django-rest-framework.org/tutorial/1-serialization/).

## Where is the admin?

It where in `breathecode/APP_NAME/serializers.py`.
