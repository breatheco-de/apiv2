

## April 13

To solve the login case sensitive issue:

```
UPDATE auth_user SET email=LOWER(email);
UPDATE authenticate_profileacademy SET email=LOWER(email);
UPDATE authenticate_userinvite SET email=LOWER(email);
```