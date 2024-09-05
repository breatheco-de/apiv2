# Serializers

A serializer is an element (a [class](https://en.wikipedia.org/wiki/Class_(computer_programming)) in this case) that translates an [object](https://en.wikipedia.org/wiki/Object_(computer_science)) ([Object-oriented programming](https://en.wikipedia.org/wiki/Object-oriented_programming)) and generates an output that should be useful for something. In Django, a serializer is used to format the object before it is sent. We are using the [Django Rest Framework](https://www.django-rest-framework.org) Serializers for POST and PUT methods, and for the GET method we are using [Serpy](../../serpy/) because it is faster than DRF Serializers.

Related articles:

- [HTTP](https://en.wikipedia.org/wiki/HTTP)
- [REST](https://en.wikipedia.org/wiki/REST)

## Writing Serializers

Read [this](https://www.django-rest-framework.org/tutorial/1-serialization/).

## Where are the serializers?

They are located in `breathecode/APP_NAME/serializers.py`.
