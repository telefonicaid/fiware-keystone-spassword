#!/usr/bin/python
"""
  python ./keystone_ldap_schema.py cn=openstack,cn=org openstack > /tmp/openstack_schema.ldif
"""
import sys

if sys.argv.__len__() < 3:
    usage = """
USAGE: {0} subtree organization

{0} Generates an LDIF file that can then be added to a Directory server via 
the ldapadd command.  The Schema is in the format expected by the LDAP 
Identity Driver in Keystone
"""
    print usage.format(sys.argv[0])
    sys.exit(1)

subtree=sys.argv[1]
organization=sys.argv[2]
ldif_file="""
dn: {0}
objectClass: dcObject
objectClass: organization
o: {1}
dc: {1}

dn: ou=groups,{0}
objectClass: organizationalUnit
objectClass: top
ou: groups

dn: ou=users,{0}
objectClass: organizationalUnit
objectClass: top
ou: users

dn: ou=roles,{0}
objectClass: organizationalUnit
objectClass: top
ou: roles"""

print ldif_file.format(subtree,organization)
