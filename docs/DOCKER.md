The following environment variables are available for keystone-spassword docker

| Environment variable        | Configuration attribute     | Default value           |
|:----------------------------|:----------------------------|:------------------------|
| SPASSWORD_ENABLED           | spassword enabled           | True                    |
| SPASSWORD_PWD_MAX_TRIES     | spassword pwd_max_tries     | 5                       |
| SPASSWORD_PWD_BLOCK_MINUTES | spassword pwd_block_minutes | 30                      |
| SPASSWORD_PWD_EXP_DAYS      | spassword pwd_exp_days      | 365                     |
| SPASSWORD_SMTP_SERVER       | spassword smtp_server       | 0.0.0.0                 |
| SPASSWORD_SMTP_PORT         | spassword smtp_port         | 587                     |
| SPASSWORD_SMTP_TLS          | spassword smtp_tls          | True                    |
| SPASSWORD_SMTP_USER         | spassword smtp_user         | smtpuser@yourdomain.com |
| SPASSWORD_SMTP_PASSWORD     | spassword smtp_password     | yourpassword            |
| SPASSWORD_SMTP_FROM         | spassword smtp_from         | smtpuser                |
| SPASSWORD_SNDFA             | spassword sndfa             | False                   |
| SPASSWORD_SNDFA_ENDPOINT    | spassword sndfa_endpoint    | localhost:5001          |
| SPASSWORD_SNDFA_TIME_WINDOW | spassword sndfa_time_window (hours) | 24              |
| TOKEN_EXPIRATION_TIME       | token expiration (seconds)  | 10800                   |
| REVOKE_EXPIRATION_BUFFER    | revoke expiration_buffer    | 1800                    |
| REDIS_ENDPOINT              | cache backend_argument      | N/A                     |
| LOG_LEVEL                   | n/a                         | INFO                    |
| ROTATE_FERNET_KEYS          | n/a                         | True                    |
| SAML_ENDPOINT               | Keystone Endpoint used to expose SAML API for idp and sso options  | N/A            |
| SAML_CERTFILE               | File location for SSL signing certificate (certfile)    | N/A            |
| SAML_KEYFILE                | File location for SSL signing key (keyfile)             | N/A            |

