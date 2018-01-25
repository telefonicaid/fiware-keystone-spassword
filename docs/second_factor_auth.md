# Second Factor Authentication (2FA)

## Configuration

Specific options at /etc/keystone/keystone.conf
```
[spassword]
sndfa=true
sndfa_time_window=24
```

## API

Second Factor authentication introduces new methods:

GET /v3/users/<user_id>/checkemail

GET /v3/users/<user_id>/checkemail/<code>
  without x-auth-token

POST /v3/users/<user_id>/sndfa

GET /v3/users/<user_id>/sndfa/<code>

GET /v3/users/<user_id>/recover_password

