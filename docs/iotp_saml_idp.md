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
