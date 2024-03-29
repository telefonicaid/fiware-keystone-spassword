# Integrate LDAP into IoTP Keystone


- [Describe Solution](#describe-solution)
- [Requirements](#requirements)
- [Install and Configure a LDAP](#install-ldap)
  - [Configure LDAP](#configure-ldap)
  - [Populate LDAP](#populate-ldap)
  - [Adapt existing LDAP](#adapt-existing-ldap)
- [Configure Keystone for use a LDAP](#configure-keystone)


## Describe Solution

This document describe how to integrate a LDAP with IoTPlatform Identity Management tool (Keystone) for external user authentication.

This solution assumes that:
- IoTPlatform uses Orchestrator and Keystone.
- Orchestrator is used to provision new services. This way Orchestrator creates roles, groups and policies when a new service (keystone domain) is created.
- Keystone with SCIM and SPASSWORD plugins.
- Specific details about keystone usage in IoTP was described in [fiware-iot-stack.readthedocs](https://fiware-iot-stack.readthedocs.io/en/latest/topics/user_permissions/index.html).

The solution will use a Read Only LDAP for keystone authentication feature and a SQL driver for Keystone assignment feature.
The solution will enable [Domain Specific Configuration](http://docs.openstack.org/admin-guide/identity-domain-specific-config.html) for Keystone which imples that each domain could use a different configuration. In this case each domain will have a specific LDAP configuration (endpoint, connection values, etc).

LDAP will provide Users and Groups. Groups are handled and provisioned in Keystone by IoTP Orchestrator.
User authentication will be done throght LDAP directory.

This solution about integrate LDAP with Keystone expects:
- Users are in LDAP for authentication: name, description, email, password.
- Users in LDAP could belong to LDAP groups.
- Both LDAP Users and LDAP Groups could be asigned to IoT Platform roles, as described in [user role assigment API](https://orchestrator2.docs.apiary.io/#reference/orchestrator/user-role-assigment) and [group role assignment API](https://orchestrator2.docs.apiary.io/#reference/orchestrator/group-role-assigment) and [IoT Platform roles](https://thinking-cities.readthedocs.io/en/master/topics/user_permissions/index.html)
- Optionally IoTPlatform, through Orchestrator (since version 1.5.0 or upper), could create a predefined groups when create a new Service which are:
  - ServiceCustomerGroup: with role ServiceCustomer assigned in service.
  - SubServiceCustomerGroup: with role SubServiceCustomer assigned in all posible subservices
  - SubServiceAdminGroup: with role SubServiceAdmin assigned in all posible subservices
  - AdminGroup: with roles admin in service and SubServiceAdmin assigned in all posible subservices
  

## Requirements

### Software Requirements:
  - [OpenStack Keystone](http://docs.openstack.org/developer/keystone) version Liberty or upper.
  - [Keystone SPASSWORD plugin](https://github.com/telefonicaid/fiware-keystone-spassword) plugin 1.2.0 or upper.
  - [Keystone SCIM plugin](https://github.com/telefonicaid/fiware-keystone-scim) plugin version 1.1.7 or upper.
  - [IoTP Orchestrator](https://github.com/telefonicaid/orchestrator) version 1.5.0 or upper.
  - External LDAP: [OpenLDAP](http://www.openldap.org) 2.4.40 or upper.


## Install and configure a LDAP (not exists previous LDAP)

This procedure describe how to install from the scratch and configure a new LDAP instance in order to be used as external LDAP for keystone authentication.

OpenLDAP is a free, open source implementation of the Lightweight Directory Access Protocol (LDAP) developed by the OpenLDAP Project. It is released under its own BSD-style license called the OpenLDAP Public License.


#### Debian/Ubuntu: sldap
```
 $ sudo apt-get install slapd ldapscripts
```

#### Centos/RedHat 7: openldap-servers
```
 $ sudo yum install openldap-servers
```

### Configure LDAP

#### Debian/Ubuntu: (recomended)
Set Domain Name to "openstack.org", set organization to "openstack" and give a password.

```
 $ dpkg-reconfigure slapd
```

#### Centos/RedHat 7:
Follow this guide about [install an OpenLDAP for Keystone](https://wiki.openstack.org/wiki/OpenLDAP).

```
 $ slappasswd -h {SSHA} -s <password>
 $ sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f ./manager.ldif
 $ sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/openldap/schema/cosine.ldif
 $ sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/openldap/schema/nis.ldif 
 $ sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/openldap/schema/inetorgperson.ldif
```


#### Docker container:
You can also easily deploy a openldap container:

```
 $ sudo docker run \
          --name my-openldap-container \
          --env LDAP_ORGANISATION="openstack" \
          --env LDAP_DOMAIN="openstack.org" \
          --env LDAP_ADMIN_PASSWORD="<ldap_admin_password>" \
          --detach -p 389:389 osixia/openldap:1.5.0
```

### Populate LDAP

The following steps are needed to populate a LDAP with users and groups.

- Configuracion schema [keystone_ldap_schema](./keystone_ldap_schema.py)
```
 $ python ./keystone_ldap_schema.py dc=openstack,dc=org openstack > /tmp/openstack_schema.ldif
 $ ldapadd -x -c -W -D"cn=admin,dc=openstack,dc=org" -f /tmp/openstack_schema.ldif
```

- Add a new User to LDAP: [user template](./user.ldif)
```
 $ ldapadd -x -c -W -D "cn=admin,dc=openstack,dc=org" -f user.ldif
 $ ldappasswd -s <ldap_admin_password> -W -D "cn=admin,dc=openstack,dc=org" -x "uid=adm,ou=users,dc=openstack,dc=org"
```

- Add a new Group to LDAP with their users [group template](./group.ldif)
```
 $ ldapadd -x -c -W -D "cn=admin,dc=openstack,dc=org" -f group.ldif
```

#### Populate LDAP (for ldap in a docker container)

The following steps are the same that above but for the case of LDAP is in a docker like proposed:

- Configuracion schema [keystone_ldap_schema](./keystone_ldap_schema.py)
```
 $ python ./keystone_ldap_schema.py dc=openstack,dc=org openstack > /tmp/openstack_schema.ldif
```
- Copy ldif files to container:
```
 $ sudo docker cp /tmp/openstack_schema.ldif my-openldap-container:/tmp
 $ sudo docker cp group.ldif my-openldap-container:/tmp
 $ sudo docker cp user.ldif my-openldap-container:/tmp
```

- Check ldap docker container configuration:
```
 $ sudo docker exec my-openldap-container ldapsearch -x -h localhost -b dc=openstack,dc=org -D "cn=admin,dc=openstack,dc=org" -w <ldap_admin_password>
```

- Configure and populate:
```
 $ sudo docker exec my-openldap-container ldapadd -x -c -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -f /tmp/openstack_schema.ldif

 $ sudo docker exec my-openldap-container ldapadd -x -c -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -f /tmp/user.ldif

 $ sudo docker exec my-openldap-container ldappasswd -s <ldap_admin_password> -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -x "uid=adm,ou=users,dc=openstack,dc=org"

 $ sudo docker exec my-openldap-container ldapadd -x -c -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -f /tmp/group.ldif
```

- Check ldap docker final ldap configuration:
```
 $ sudo docker exec my-openldap-container ldapsearch -x -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -b "dc=openstack,dc=org" "(objectclass=*)"

```


### Adapt existing LDAP (creating groups)

In order of discover existing users and groups in already configured LDAP you should try to run a command like
```
ldapsearch -x -h localhost -w <ldap_admin_password> -D "cn=admin,dc=openstack,dc=org" -b "dc=openstack,dc=org" "(objectclass=*)"
```

In case you have a previous LDAP with users already provisioned, you need to group them into the following groups in order to match with IoTPlatform access control policies (described in [fiware-iot-stack.readthedocs.io](https://fiware-iot-stack.readthedocs.io/en/latest/topics/user_permissions/index.html#users-and-permissions)

  - ServiceCustomerGroup
  - SubServiceCustomerGroup
  - SubServiceAdminGroup
  - AdminGroup

For achive that you have to create that groups, with that names, in your LDAP. For example, if you have adm and foo users in your LDAP and you want to that users belongs to AdminGroup, then in a one step you can create AdminGroup and assign users to that group:

```
 $ ldapadd -x -W -D "cn=admin,dc=openstack,dc=org" -f add_admin_group.ldif
```


## Configure Keystone

In order to configure keystone for LDAP integration you should get into Keystone host and perform the following steps:


- Configure SELinux values (if SElinux is running):

```
   $ setsebool -P authlogin_nsswitch_use_ldap on
```

# Keystone with spassword plugin version until 1.3.0

- Enable Domain Specific Configuration in Keystone

```
   $ mkdir /etc/keystone/domains
   $ chown keystone.keystone /etc/keystone/domains
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_specific_drivers_enabled true
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity domain_config_dir /etc/keystone/domains
```
  Copy your keystone.DOMAIN_NAME.conf into /etc/keystone/domains. Use [keystone.smartcity.conf](./keystone.smartcity.conf) as a template. Remember change <YOUR_LDAP_IP> with a proper IP on that file.

  You will need such a keystone.smartcity.conf files as services (keystone domains) will use LDAP authentication.


```
   $ chown keystone.keystone /etc/keystone/domains/*
```

  Copy driver [sql_ldap.py](../docker/sql_ldap.py) into /usr/lib/python2.7/site-packages/keystone/identity/mapping_backends directory. This driver is unique for all services (keystone domains) that use LDAP authentication.

```
   $ cp sql_ldap.py  /usr/lib/python2.7/site-packages/keystone/identity/mapping_backends
```


- Define Generic LDAP configuration:

```
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap url ldap://<YOUR_LDAP_IP>
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap user dc=admin,dc=openstack,dc=org
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap password <ldap_admin_password>
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap suffix openstack,dc=org
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap query_scope sub
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap page_size 0
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap alias_dereferencing default
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap use_pool true
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap pool_size 10
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap pool_retry_max 3
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap pool_retry_delay 0.1
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap pool_connection_timeout -1
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap pool_connection_lifetime 600
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap use_auth_pool false
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap auth_pool_size 100
   $ openstack-config --set /etc/keystone/keystone.conf \
                   ldap auth_pool_connection_lifetime 60
   $ openstack-config --set /etc/keystone/keystone.conf \
                   identity_mapping driver keystone.identity.mapping_backends.sql_ldap.Mapping

```

- Truncate id_mapping table:

  In order to force mapping based on id groups is better to clean previous mapping entries.

```
   $ mysql -h iot-mysql -u root -p
   SQL> use keystone;
   SQL> truncate table id_mapping;
```

  These and other values can be modified by editing [/etc/keystone/keystone.conf](http://docs.openstack.org/liberty/config-reference/content/section_keystone.conf.html).

- Enable debug mode for logging:

  In order to allow an easy debug you can change Keystone logging level to DEBUG:

```
   $ openstack-config --set /etc/keystone/keystone.conf \
                   DEFAULT debug true
```

  or to INFO level:
```
   $ openstack-config --set /etc/keystone/keystone.conf \
                   DEFAULT verbose true
```
- Restart Keystone:
  Depending on your deploy, it could be a simple service restart:

```
  $ sudo service openstack-keystone restart
```
  or a docker container restart


# Keystone with spassword plugin version 1.4.0 or upper

Copy your keystone.DOMAIN_NAME.conf into /etc/keystone/domains. Use [keystone.smartcity.conf](./keystone.smartcity.conf) as a template. Remember change <YOUR_LDAP_IP> with a proper IP on that file.

  You will need such a keystone.smartcity.conf files as services (keystone domains) will use LDAP authentication.


- Restart Keystone:
  Depending on your deploy, it could be a simple service restart:

```
  $ sudo service openstack-keystone restart
```
  or a docker container restart
