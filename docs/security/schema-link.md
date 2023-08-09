# Schema link

It's custom authorization schema that share a key between 2 servers, it's used when you can't block microservices by ip, both servers authorize what actions can perform its pair, if both apps does not belongs to the same company you must include additionally an agreement layer.

## `When user must sign an agreement?`

When both servers does not belong to the same company, it's mandatory.

## `How is build that agreement?`

It's builded as a collection of scopes that represent what's authorized server can do with your data.

## `What's scope?`

In the context of OAuth, OpenID Connect, and many authentication/authorization systems, "scope" refers to the permissions that are associated with a particular token.

## `How to link both servers?`

Each server must register the other server in its database, it must share the same algorithm, strategy, keys and schema, and the key can't be shared, because during the keys rotations many of them will breaks.

# Objects

## `Token`

This object represent the json payload.

- `sub`: The "subject" claim in a JWT. This usually represents the principal entity (typically a user) for which the JWT is intended. In this case, user_id would be the identifier of the user in the context of your system.
- `iss`: The "issuer" claim in a JWT. This represents the entity that generated and signed the JWT. In this case, it's being read from an environment variable API_URL, with a default value of 'http://localhost:8000'.
- `app`: This is a custom claim you've defined. It appears to specify the name of the application generating the token, in this case '4geeks'.
- `aud`: The "audience" claim. This represents the intended recipients of the JWT. In this case, it's app.slug, presumably the identifier for an application that should accept this token.
- `exp`: The "expiration time" claim. This is the time after which the JWT should no longer be accepted. It's calculated as the current time now plus a certain number of minutes determined by JWT_LIFETIME.
- `iat`: The "issued at" claim. This represents the time at which the JWT was issued. It's the current time now minus one second (to ensure the token is valid immediately on issuance).
- `typ`: The "type" claim. It's a hint about the type of token. In this case, it's 'JWT' to indicate that this is a JSON Web Token.

## `App`

This object represent the app on your database, this object must be cached.

- `id`: The unique identifier for the application. This is often used as a reference to the application in the system.
- `private_key`: This is a cryptographic key that is kept secret and only known to the application. This can be used for things like signing tokens or encrypting data.
- `public_key`: This is the counterpart to the private key. It can be freely shared and is often used to verify tokens signed with the private key, or decrypt data encrypted with the private key.
- `algorithm`: This refers to the algorithm used for cryptographic operations. This could be a specific type of symmetric or asymmetric encryption, or a digital signature algorithm.
- `strategy`: This could refer to a particular strategy used for authentication or authorization in your system.
- `schema`: This could be the structure or format that the app's data follows. In the context of databases, a schema defines how data is organized and how relationships are enforced.
- `require_an_agreement`: This is likely a Boolean value (True/False) indicating whether the user needs to agree to certain terms before using the application.
- `webhook_url`: Webhooks provide a way for applications to get real-time data updates. This URL is likely where the application will send HTTP requests when certain events occur.
- `redirect_url`: In OAuth or similar authentication/authorization flows, this is the URL where users are redirected after they authorize the application. This URL often includes a code or token as a query parameter, which the application can exchange for an access token.
- `app_url`: This is likely the URL where the actual application can be accessed by users.

# Using Json Web Token

JWT stands for JSON Web Token. It is a standard (RFC 7519) for creating access tokens that assert some number of claims. For example, a server could generate a token that has the claim "logged in as admin" and provide that to a client. The client could then use that token to prove that it's logged in as admin.

A JWT is composed of three parts: a header, a payload, and a signature. These parts are separated by dots (.) and are Base64Url encoded.

- `Header`: The header typically consists of two parts: the type of the token, which is JWT, and the signing algorithm being used, such as HMAC SHA256 or RSA.

- `Payload`: The second part of the token is the payload, which contains the claims. Claims are statements about an entity (typically, the user) and additional metadata. There are three types of claims: registered, public, and private claims.

- `Signature`: To create the signature part you have to take the encoded header, the encoded payload, a secret, the algorithm specified in the header, and sign that.

The resulting string is three Base64-URL strings concatenated with dots. The string is compact, URL-safe, and can be conveniently passed in HTML and HTTP environments.

## `Params`

- `Token`: JWT token.
- `App`: App's slug that sign this token.

```http
GET /data HTTP/1.1
Host: api.example.com
Authorization: Link App={App},Token={Token}
```

# Using Signature

It's a mechanism that validates the authenticity and integrity of data. It provides a way to verify that the data came from a specific source and has not been altered in transit.

## `Params`

- App: it represents a unique identifier for the app making the request. This is included in the header so the server knows which application is making the request.
- Token: A nonce is a random or semi-random number that is generated for a specific use, typically to avoid replay attacks. In this case, it's a sign that refer to a signature generated using a cryptographic algorithm.
- SignedHeaders: This part of the header includes the list of HTTP headers that are included in the signature. These are joined into a string separated by semicolons.
- Date: This is the timestamp when the request is made. It's often used to ensure that a request is not replayed (that is, sent again by an attacker).

```http
GET /api/resource HTTP/1.1
Host: www.example.com
Authorization: Signature App={App},Nonce={Token},SignedHeaders={header1};{header2};{header3},Date={Date}
```

# Code

## `Sender Code`

Service is a requests wrapper that manage the authorization header, it use the authorization strategy specified in the app object.

```py
# Make an action over multiple users
s = Service(app.id)
request = s.get('v1/auth/user')
data = request.json()
print(data)

# Make an action over a specify user
s = Service(app.id, user.id)
request = s.get('v1/auth/user')
data = request.json()
print(data)

# Force Json Web Token as authorization strategy
s = Service(app.id)
request = s.get('v1/auth/user', mode='JWT')
data = request.json()
print(data)

# Force Json Web Token as authorization strategy
s = Service(app.id)
request = s.get('v1/auth/user', mode='SIGNATURE')
data = request.json()
print(data)
```

## Receiver

Protect a endpoint to access to it having these scopes, like the sender, @scope get `mode` as argument.

```py
@api_view(['POST'])
@permission_classes([AllowAny])
@scope(['action_name1:data_name1', 'action_name2:data_name2', ...])
def endpoint(request, app: dict, token: dict):
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
