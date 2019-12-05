
mkdir /etc/keystone/domains
chown keystone.keystone /etc/keystone/domains
openstack-config --set /etc/keystone/keystone.conf \
               identity domain_specific_drivers_enabled true
openstack-config --set /etc/keystone/keystone.conf \
                 identity domain_config_dir /etc/keystone/domains
openstack-config --set /etc/keystone/keystone.conf \
              ldap url ldap://<LDAP_IP>
openstack-config --set /etc/keystone/keystone.conf \
              ldap user dc=admin,dc=openstack,dc=org
openstack-config --set /etc/keystone/keystone.conf \
              ldap password <PWD>
openstack-config --set /etc/keystone/keystone.conf \
              ldap suffix openstack,dc=org
openstack-config --set /etc/keystone/keystone.conf \
              ldap query_scope sub
openstack-config --set /etc/keystone/keystone.conf \
              ldap page_size 0
openstack-config --set /etc/keystone/keystone.conf \
              ldap alias_dereferencing default
openstack-config --set /etc/keystone/keystone.conf \
              ldap use_pool true
openstack-config --set /etc/keystone/keystone.conf \
              ldap pool_size 10
openstack-config --set /etc/keystone/keystone.conf \
              ldap pool_retry_max 3
openstack-config --set /etc/keystone/keystone.conf \
              ldap pool_retry_delay 0.1
openstack-config --set /etc/keystone/keystone.conf \
              ldap pool_connection_timeout -1
openstack-config --set /etc/keystone/keystone.conf \
              ldap pool_connection_lifetime 600
openstack-config --set /etc/keystone/keystone.conf \
              ldap use_auth_pool false
openstack-config --set /etc/keystone/keystone.conf \
              ldap auth_pool_size 100
openstack-config --set /etc/keystone/keystone.conf \
              ldap auth_pool_connection_lifetime 60
openstack-config --set /etc/keystone/keystone.conf \
              identity_mapping driver keystone.identity.mapping_backends.sql_ldap.Mapping
              
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT debug true
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT verbose true
