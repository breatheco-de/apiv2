# Views

A view is a concept that is part of [Model-View-Controller](https://en.wikipedia.org/wiki/Model–view–controller), the view manages the appearance of the application, you could guess that in Django a view would be the template, but actually, on Django what would be a [handler](https://expressjs.com/en/guide/routing.html) in an Express like framework, because the view can build a [HTML](https://en.wikipedia.org/wiki/HTML) without using templates. On Django an Exception could return a 4xx or 5xx response.

Related articles:

- [HTTP](https://en.wikipedia.org/wiki/HTTP).
- [REST](https://en.wikipedia.org/wiki/REST).

## Writing views

Read [this](https://docs.djangoproject.com/en/5.0/topics/http/views/).

### Async views

Read [this](https://docs.djangoproject.com/en/5.0/topics/http/views/#async-views).

### Functional views

Read [this](https://docs.djangoproject.com/en/5.0/topics/http/decorators/).

### Render templates

Read [this](https://docs.djangoproject.com/en/5.0/topics/http/shortcuts/#render).

### Redirections

Read [this](https://docs.djangoproject.com/en/5.0/ref/contrib/redirects/).

## Where are the views?

It where in `breathecode/APP_NAME/views.py`.

## Where is the test file?

It where in `breathecode/APP_NAME/tests/urls/tests_ROUTE_NAME.py`.
