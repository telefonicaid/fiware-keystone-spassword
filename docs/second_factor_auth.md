# Second Factor Authentication (2FA)

According with [wikipedia](https://en.wikipedia.org/wiki/Multi-factor_authentication) Two-factor authentication (also known as 2FA) is a type (subset) of multi-factor authentication. It is a method of confirming a user's claimed identity by utilizing a combination of two different factors: 1) something they know, 2) something they have, or 3) something they are.

This feature provides 2FA for OpenStack Keystone based on email.

2FA feature extends token data returned from keystone to user by
"POST /v3/auth/tokens", including new fields in 'extra' dictionary of 'token':

```
 "extras": {
     ...
     "sndfa": true
     "sndfa_email": true
     ...
     },
```

## Configuration

Specific options at /etc/keystone/keystone.conf
```
[spassword]
sndfa=true
sndfa_time_window=24
sndfa_endpoint='localhost:5001'
```

* `sndfa` is a boolean which enables (true) or disables (false) if Second Factor Authentication feature is available in Keystone instance.
* `sndfa_time_window` indicates the time in hours in which Second Factor Authentication performed by an user is still valid before ask another new one.
* `sndfa_endpoint` is the endpoint used in links sent by email to users to check email address and sndfa changes


In order to work with Second Factor Authentication feature spassword needs a proper smtp configuration; make sure that you provide one.

```
[spassword]
smtp_server=localhost
smtp_port=587
smtp_tls=true
smtp_user='smtpuser@yourdomain.com'
smtp_password='yourpassword'
smtp_from='smtpuser'
```

## API

Second Factor authentication introduces new methods:

- Ask to check current user email. A code will be sent to user to that email.
  
  ```GET /v3/users/<user_id>/checkemail```

- Check a code to validate user email. The code was received by user in his email.
  
  ```GET /v3/users/<user_id>/checkemail/<code>```
  
  This call does not need a x-auth-token. Tipically is done by click in an email link.

- Modify configuration for second factor authentication for a user, allowing enable or disable it.
  
  ```POST /v3/users/<user_id>/sndfa```

- Check a second factor authentication code to allow user authentication. Code is just valid during sndfa_time_window.
  
  ```GET /v3/users/<user_id>/sndfa/<code>```
  
  This call does not need a x-auth-token. Tipically is done by click in an email link.

- Force to recover a user passsword.
  
  ```GET /v3/users/<user_id>/recover_password```
  
  This call does not need a x-auth-token
