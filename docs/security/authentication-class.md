# Authentication classes

## `ExpiringTokenAuthentication`

it's the default authentication class implemented in 4Geeks.

ExpiringTokenAuthentication is integral to the security of our Django web application. Its main purpose is to handle user authentication, i.e., verifying that a user is who they claim to be.

```vbnet
GET /v1/resource/path HTTP/1.1
Host: www.example.com
Authorization: Token your_token_here
```

The ExpiringTokenAuthentication class within it provides a specific type of token-based authentication. Unlike simple token-based authentication where tokens remain valid indefinitely, this class ensures that tokens expire after a certain period (24 hours in this case). This means that even if an attacker manages to get hold of a token, they can only use it for a limited time.

Upon receiving a request, the system checks the provided token, confirms it's valid and hasn't expired, and identifies the user associated with the token. If any of these checks fail, an AuthenticationFailed exception is raised, denying access.

```http
POST /v1/auth/login HTTP/1.1
Host: www.example.com
Content-Type: application/json

{
  "username": "john.doe",
  "password": "supersecretpassword"
}
```
