# Integrate LDAP into IoTP Keystone


* [Describe Solution](#describe-solution)
* [Requirements](#requirements)
* [Install & Configure a LDAP](#install-ldap)
* [Populate a LDAP](#populate-ldap)
* [Configure Keystone for use a LDAP](#configure-keystone)


## Describe Solution

This document describe how to integrate a LDAP with IoTPlatform Identity Management tool (Keystone) for external user authentication.

This solution assumes that:
- IoTPlatform uses Orchestrator and Keystone.
- Orchestrator is used to provision new services. This way orchestrator creates role, groups and policies when a new service (keystone domain) is created.
- Keystone with SCIM and SPASSWORD plugins.
- Specific details about keystone usage in IoTP was described in [rtd](https://fiware-iot-stack.readthedocs.io/en/latest/topics/user_permissions/index.html).

The solution will use a Read Only LDAP for keystone authentication feature and a SQL driver for Keystone assignment feature.
The solution will enable [Domain Specific Configuration](http://docs.openstack.org/admin-guide/identity-domain-specific-config.html) for Keystone which imples that each domain could use a different configuration. In this case each domain will have a specific LDAP configuration (endpoint, connection values, etc).

LDAP will provide Users and Groups. Groups are handled and provisioned in Keystone by IoTP Orchestrator.
User authentication will be done throght LDAP directory.

This solution about integrate LDAP with Keystone expects:
- Users are in LDAP for autentication: name, description, email, password.
- The following groups are defined in LDAP:
  - ServiceCustomerGroup
  - SubServiceCustomerGroup
  - SubServiceAdminGroup
  - AdminGroup
  These groups has been provisioned automatically by IoTP Orchestrator in each Service.
- Users in LDAP belongs to the defined LDAP Groups.


## Requirements

### Software Requirements:
  - [OpenStack Keystone](http://docs.openstack.org/developer/keystone) version Liberty.
  - [Keystone SPASSWORD plugin](https://github.com/telefonicaid/fiware-keystone-spassword) plugin 1.1.2 or upper.
  - [Keystone SCIM plugin](https://github.com/telefonicaid/fiware-keystone-scim) plugin version 1.1.7 or upper.
  - [IoTP Orchestrator](https://github.com/telefonicaid/orchestrator) version 1.5.0 or upper.
  - External LDAP: [OpenLDAP](http://www.openldap.org) 2.4.40 or upper.


## Install and configure LDAP

OpenLDAP is a free, open source implementation of the Lightweight Directory Access Protocol (LDAP) developed by the OpenLDAP Project. It is released under its own BSD-style license called the OpenLDAP Public License.

#### Debian/Ubuntu): sldap
```
 $ sudo apt-get install sldap
```

#### Centos/RedHat 7: openldap-servers
```
 $ sudo yum install opensldap-server
```

### Configure LDAP

#### Debian/Ubuntu):
Set Domain Name to "openstack.org and set organization to "openstack".

```
 $ dpkg-reconfigure slapd
```

#### Centos/RedHat 7
Follow this guide about [install an OpenLDAP for Keystone](https://wiki.openstack.org/wiki/OpenLDAP).


## Populate LDAP

The following steps are needed to populate a LDAP with users and groups.

- Configuracion schema [keystone_ldap_schema](./keystone_ldap_schema.py)
```
 $ python ./keystone_ldap_schema.py cn=openstack,cn=org openstack > /tmp/openstack_schema.ldif
 $ ldapadd -x -W -D"cn=admin,dc=openstack,dc=org" -f /tmp/openstack_schema.ldif
```

- Add a new User to LDAP: [user template](./user.ldif)
```
 $ ldapadd -x -W -D "cn=admin,dc=openstack,dc=org" -f user.ldif
 $ ldappasswd -s 4pass1w0rd -W -D "cn=admin,dc=openstack,dc=org" -x "uid=adm1,ou=users,dc=openstack,dc=org"
```

- Add a new Group to LDAP with their users [group template](./group.ldif)
```
 $ ldapadd -x -W -D "cn=admin,dc=openstack,dc=org" -f group.ldif
```


## Configure Keystone

- Configure SELinux values:

```
 $ setsebool -P authlogin_nsswitch_use_ldap on
```

- Enable Domain Specific Configuration in Keystone

```
   $ mkdir /etc/keystone/domains
   $ chown keystone.keystone /etc/keystone/domains
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_scpecific_drivers enabled
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_config_dir /etc/keystone/domains
```
  Copy your DOMAIN_NAME.conf into /etc/keystone/domains. Use [keystone.smartcity.conf](./keystone.smartcity.conf) as a template.

  Copy driver (id_group_lda.py)[./id_group_ldap.py] into /usr/lib/python2.7/site-packages/keystone/identity/mapping_backends directory.

- Define Generic LDAP configuration:

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

  These and other values can be modified by editing [keystone.conf](http://docs.openstack.org/liberty/config-reference/content/section_keystone.conf.html).

- Restart Keystone