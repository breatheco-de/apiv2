# `Token`

This object represents the JSON payload.

- `sub`: user.id.
- `iss`: the host of the service, example `"http://localhost:8000"``.
- `app`: app that made the token, for example `"4geeks"`.
- `aud`: app that will receive the request.
- `exp`: token expiration time.
- `iat`: time when the token was issued.
- `typ`: token type (default `"JWT"`).
