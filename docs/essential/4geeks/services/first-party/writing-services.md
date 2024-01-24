# Writing services

We have a wrapper that implements a [first-party](../introduction.md) endpoint to be used by some first-party services.

## Arguments

Both, the [decorator](https://en.wikipedia.org/wiki/Python_syntax_and_semantics#Decorators) `scope` accepts the following arguments:

- `scopes`: `[scope1.slug, scope2.slug, ...]`
- `mode`: `"signature"` or `"jwt"` (default)

## Signature mode vs JWT mode

When JWT is used, it just signs a token with the data of the user, while the signature signs the token with all the content of the request to verify the source of the request. JWT is significantly faster than using signatures.

## Syncronomous implementation

Service is a [Requests](../../../requests.md) wrapper, you should use this library like it was Requests, and the [host](https://en.wikipedia.org/wiki/Hostname) is resolved automatically.

### making a request signed in as 4geeks

```py
from rest_framework.views import APIView
from breathecode.utils.decorators.scope import scope

class AppUserView(APIView):
    permission_classes = [AllowAny]

    @scope(['read:user'])
    def get(self, request, app: dict, token: dict, user_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        extra = {}
        if app.require_an_agreement:
            extra['appuseragreement__app__id'] = app.id

        if token.sub:
            extra['id'] = token.sub

        if user_id:
            if token.sub and token.sub != user_id:
                raise ValidationException(translation(lang,
                                                      en='This user does not have access to this resource',
                                                      es='Este usuario no tiene acceso a este recurso'),
                                          code=403,
                                          slug='user-with-no-access',
                                          silent=True)

            if 'id' not in extra:
                extra['id'] = user_id

            user = User.objects.filter(**extra).first()
            if not user:
                raise ValidationException(translation(lang, en='User not found', es='Usuario no encontrado'),
                                          code=404,
                                          slug='user-not-found',
                                          silent=True)

            serializer = AppUserSerializer(user, many=False)
            return Response(serializer.data)

        # test this path
        items = User.objects.filter(**extra)
        items = handler.queryset(items)
        serializer = AppUserSerializer(items, many=True)

        return handler.response(serializer.data)
```

## Asyncronomous implementation

Not implemented yet.
