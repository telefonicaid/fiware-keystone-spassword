# Integrate LDAP into IoTP Keystone


* [Solution](#solution)
* [Requirements](#requirements)
* [Install LDAP](#install-ldap)
* [Configure LDAP](#configure-ldap)
* [Populate LDAP](#populate-ldap)
* [Configure Keystone for use an LDAP](#configure-keystone)


## Describe Solution

This document describe how to integrate a LDAP with IoTPlatform Identity Management tool (Keystone) for external user authentication.

This solution assumes that:
- IoTPlatform uses Orchestrator and Keystone.
- Orchestrator is used to provision new services. This way orchestrator creates role, groups and policies when a new service (keystone domain) is created.
- Keystone with SCIM and SPASSWORD plugins.
- Specific details about keystone usage in IoTP was described in [here](https://fiware-iot-stack.readthedocs.io/en/latest/topics/user_permissions/index.html)

The solution will use a Read Only LDAP for authentication.

The solution will use [Domain Specific Configuration](http://docs.openstack.org/admin-guide/identity-domain-specific-config.html) for Keystone which imples that each domain could use a different configuration. In this case each domain will have a specific LDAP configuration (endpoint, connection values, etc).

LDAP will provide Users ands Group. Groups are be handled in keystone and provisioned by Orchestrator
User authentication will be done throght LDAP directory.

This solution about integrate LDAP with Keystone expects:
- Users are in LDAP for autentication: name, description, email, password.
- The following groups are defined in LDAP:
  - ServiceCustomerGroup
  - SubServiceCustomerGroup
  - SubServiceAdminGroup
  - AdminGroup
- Users in LDAP belongs to the defined LDAP Groups.


## Requirements

### Software Requirements:
  - [Keystone](http://docs.openstack.org/developer/keystone) version Liberty.
  - Keystone [SPASSWORD](https://github.com/telefonicaid/fiware-keystone-spassword) plugin 1.1.2 or upper.
  - Keystone [SCIM](https://github.com/telefonicaid/fiware-keystone-scim) plugin version 1.1.7 or upper.
  - [Orchestrator](https://github.com/telefonicaid/orchestrator) version 1.5.0 or upper.
  - External LDAP: [OpenLDAP](https://wiki.openstack.org/wiki/OpenLDAP) 2.4.40 or upper.


## Install LDAP

### Debian/Ubuntu): sldap (2.4.40)
```
 $ sudo apt-get install sldap
```

### Centos/RedHat 7: openldap-servers  (2.4.40)
```
 $ sudo yum install opensldap-server
```


## Configure LDAP

https://wiki.openstack.org/wiki/OpenLDAP


### Populate LDAP

The following steps are needed to populate a LDAP with users and groups:

- Configuracion schema
```
 $ python ./keystone_ldap_schema.py cn=openstack,cn=org openstack > /tmp/openstack_schema.ldif
 $ ldapadd -x -W -D"cn=admin,dc=openstack,dc=org" -f /tmp/openstack_schema.ldif
``` 

- Add a new User to LDAP:
```
 $ ldapadd -x -W -D "cn=admin,dc=openstack,dc=org" -f user.ldif
 $ ldappasswd -s 4pass1w0rd -W -D "cn=admin,dc=openstack,dc=org" -x "uid=adm1,ou=users,dc=openstack,dc=org"
```

- Add a new Group to LDAP with their users
```
 $ ldapadd -x -W -D "cn=admin,dc=openstack,dc=org" -f group.ldif
``` 


## Configure Keystone

- Disable SELinux auth config

```
 $ setsebool -P authlogin_nsswitch_use_ldap on
```

- Enable Domain specific configuration:

```
   $ mkdir /etc/keystone/domains
   $ chown keystone.keystone /etc/keystone/domains   
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_scpecific_drivers enabled
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_config_dir /etc/keystone/domains
```
  Copy your DOMAIN_NAME.conf into /etc/keystone/domains. Use [keystone.smartcity.conf](./keystone.smartcity.conf) as a template.

  Copy driver (id_group_lda.py)[./id_group_ldap.py] into /usr/lib/python2.7/site-packages/keystone/identity.

- Generic LDAP configuration:

```
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap url ldap://YOUR_LDAP_IP
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap user dc=admin,dc=openstack,dc=org
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap password 4pass1w0rd
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap suffix openstack,dc=org
```

  These and other values can be modified by edition [keystone.conf](http://docs.openstack.org/liberty/config-reference/content/section_keystone.conf.html)
 


