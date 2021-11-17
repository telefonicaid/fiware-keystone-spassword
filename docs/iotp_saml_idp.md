# Configure Keystone to enable SAML2 to act as IDP

One of the configuration models supported by Keystone for federated identity is  Keystone as Identity Provider (IdP).


## Configuration
Based on [Keystone as an Identity Provider](https://docs.openstack.org/keystone/stein/admin/federation/configure_federation.html#keystone-as-idp)

These new DOCKER options should be used:

- SAML_ENDPOINT
This env var will be expanden in /etc/keystone keystone.conf

```
[saml]
idp_entity_id=https://$SAML_ENDPOINT/v3/OS-FEDERATION/saml2/idp
idp_sso_endpoint=https://$SAML_ENDPOINT/v3/OS-FEDERATION/saml2/sso
```

- SAML_CERTFILE
This env var will be expanden in /etc/keystone keystone.conf

```
[saml]
certfile=/etc/keystone/ssl/certs/signing_cert.pem
```

- SAML_KEYFILE
This env var will be expanden in /etc/keystone keystone.conf

```
[saml]
keyfile=/etc/keystone/ssl/private/signing_key.pem
```

And then a Service Provider must be created and registered into IdP Keystone.
To achive that get into container and set following env vars:

```
export KEYSTONE_HOST="127.0.0.1:5001"
export OS_USERNAME=admin
export OS_PROJECT_NAME=admin
export OS_USER_DOMAIN_ID=default
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_ID=default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL=http://127.0.0.1:5001/v3
export OS_IDENTITY_API_VERSION=3
export OS_PASSWORD='<password>'
```

and then execute the followign command with proper urls:

```
$ openstack service provider create anothersp \
--service-provider-url https://anothersp.org/Shibboleth.sso/SAML2/ECP
--auth-url https://keystone.idp.org/v3/OS-FEDERATION/identity_providers/keystoneidp/protocols/saml2/auth
```
