#!/bin/bash

KEYSTONE_ADMIN_PASSWORD=4pass1w0rd
MYSQL_ROOT_PASSWORD="iotonpremise"

DB_HOST_ARG=${1}
# DB_HOST_VALUE can be hostname[:port]
DB_HOST_VALUE=${2}
DB_HOST_NAME="$(echo "${DB_HOST_VALUE}" | awk -F: '{print $1}')"
DB_HOST_PORT="$(echo "${DB_HOST_VALUE}" | awk -F: '{print $2}')"
# Default MySQL port 3306
[[ "${DB_HOST_PORT}" == "" ]] && DB_HOST_PORT=3306

DEFAULT_PASSWORD_ARG=${3}
DEFAULT_PASSWORD_VALUE=${4}

MYSQL_PASSWORD_ARG=${5}
MYSQL_PASSWORD_VALUE=${6}

if [ "$DEFAULT_PASSWORD_ARG" == "-default_pwd" ]; then
    KEYSTONE_ADMIN_PASSWORD=$DEFAULT_PASSWORD_VALUE
fi

if [ "$MYSQL_PASSWORD_ARG" == "-mysql_pwd" ]; then
    MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD_VALUE"
fi

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     database connection mysql://keystone:keystone@$DB_HOST_NAME:$DB_HOST_PORT/keystone;

fi

/usr/bin/keystone-all &
keystone_all_pid=`ps -a | grep keystone-wsgi-public | awk '{print $1}'`
sleep 5    

export OS_SERVICE_TOKEN=ADMIN
export OS_SERVICE_ENDPOINT=http://127.0.0.1:35357/v2.0
export KEYSTONE_HOST="127.0.0.1:5001"


# Get Domain Admin Id form domain if Liberty or minor or project if Mitaka or uppper
ID_ADMIN_DOMAIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from domain d, project p where d.name="admin_domain" or p.name="admin_domain";' | awk '{if ($6=="admin_domain") print $5; else if ($2=="admin_domain") print $1}'`


curl -s -L --insecure https://github.com/openstack/keystone/raw/newton-eol/etc/policy.v3cloudsample.json \
  | jq ' .["identity:scim_create_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_list_roles"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_get_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_update_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_delete_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_get_service_provider_configs"]=""
     | .["identity:get_domain"]=""
     | .admin_and_user_filter="role:admin and \"%\":%(user.id)%"
     | .admin_and_project_filter="role:admin and \"%\":%(scope.project.id)%"
     | .["identity:list_role_assignments"]="rule:cloud_admin or rule:admin_on_domain_filter or rule:cloud_service or rule:admin_and_user_filter or rule:admin_and_project_filter"
     | .["identity:list_projects"]="rule:cloud_admin or rule:admin_and_matching_domain_id or rule:cloud_service"
     | .cloud_admin="rule:admin_required and domain_id:'${ID_ADMIN_DOMAIN}'"
     | .cloud_service="rule:service_role and domain_id:'${ID_ADMIN_DOMAIN}'"' \
  | tee /etc/keystone/policy.json

/usr/bin/keystone-manage db_sync

# Set another ADMIN TOKEN
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT admin_token $KEYSTONE_ADMIN_PASSWORD


kill -9 $keystone_all_pid
sleep 3
chkconfig openstack-keystone on

IOTAGENT_ID=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="iotagent"' | awk '{if ($2=="iotagent") print $1}'`
ID_CLOUD_ADMIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="cloud_admin"' | awk '{if ($2=="cloud_admin") print $1}'`
ID_CLOUD_SERVICE=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="pep"' | awk '{if ($2=="pep") print $1}'`

# Exclude some users from spassword
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_user_blacklist $ID_CLOUD_ADMIN,$ID_CLOUD_SERVICE,$IOTAGENT_ID

# Ensure db is migrated to current keystone version
/usr/bin/keystone-manage db_sync
/usr/bin/keystone-manage db_sync --extension spassword
