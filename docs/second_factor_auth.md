# Second Factor Authentication (2FA)

According with [wikipedia](https://en.wikipedia.org/wiki/Multi-factor_authentication) Two-factor authentication (also known as 2FA) is a type (subset) of multi-factor authentication. It is a method of confirming a user's claimed identity by utilizing a combination of two different factors: 1) something they know, 2) something they have, or 3) something they are.

This feature provider 2FA for OpenStack Keystone based on email.

## Configuration

Specific options at /etc/keystone/keystone.conf
```
[spassword]
sndfa=true
sndfa_time_window=24
sndfa_link_host='localhost:5001'
```

`sndfa` is a boolean which enables (true) or disables (false) if Second Factor Authentication feature is available in Keystone instance.
`sndfa_time_window` indicates the time in hours in which Second Factor Authentication performed by an user is still valid before ask another new one.
`sndfa_link_host`


In order to work with Second Factor Authentication feature needs spassword a proper smtp configuration; make sure that you provide one.

```
[spassword]
smtp_host=localhost
smtp_port=587
smtp_tls=true
smtp_user='smtpuser@yourdomain.com'
smtp_password='yourpassword'
smtp_from='smtpuser'
```

## API

Second Factor authentication introduces new methods:

- Ask to check current user email. A code will be sent to user to that email.
GET /v3/users/<user_id>/checkemail

- Check a code to validate user email. The code was received by user in his email.
GET /v3/users/<user_id>/checkemail/<code>
  This call does not need a x-auth-token. Tipically is done by click in a email link.

- Modify configuration for second factor authentication for a user, allowing enable or diseble it.
POST /v3/users/<user_id>/sndfa

- Check a second factor authentication code to allow user authentication
GET /v3/users/<user_id>/sndfa/<code>
  This call does not need a x-auth-token. Tipically is done by click in a email link.

- Force to recover a user passsword.
GET /v3/users/<user_id>/recover_password
  This call does not need a x-auth-token
