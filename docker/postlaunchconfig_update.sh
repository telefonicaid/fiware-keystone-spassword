#!/bin/bash

echo "INFO: postlaunchconfig_update INI"

KEYSTONE_ADMIN_PASSWORD=keystone
MYSQL_ROOT_PASSWORD=""

# Check argument DB_HOST
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
    KEYSTONE_ADMIN_PASSWORD=${DEFAULT_PASSWORD_VALUE}
fi

if [ "$MYSQL_PASSWORD_ARG" == "-mysql_pwd" ]; then
    MYSQL_ROOT_PASSWORD="${MYSQL_PASSWORD_VALUE}"
fi

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:${KEYSTONE_ADMIN_PASSWORD}@${DB_HOST_VALUE}/keystone;
fi

echo "INFO: First start of /usr/bin/keystone-all"
/usr/bin/keystone-all &
keystone_all_pid=`echo $!`
sleep 5    

# TODO: Get admin id

export SERVICE_TOKEN=${KEYSTONE_ADMIN_PASSWORD}
export SERVICE_ENDPOINT=http://127.0.0.1:35357/v2.0
export KEYSTONE_HOST="127.0.0.1:5001"

ID_ADMIN_DOMAIN=`mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -ukeystone --password=${KEYSTONE_ADMIN_PASSWORD} -e 'use keystone; select * from domain where name="admin_domain";' | awk '$2=="admin_domain" {print $1}'`
echo "ID_ADMIN_DOMAIN: ${ID_ADMIN_DOMAIN}"

echo "INFO: Create and update policies"
curl -s -L --insecure https://github.com/openstack/keystone/raw/liberty-eol/etc/policy.v3cloudsample.json \
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

echo "INFO: Launch /usr/bin/keystone-manage db_sync"
/usr/bin/keystone-manage db_sync

echo "INFO: Set another ADMIN TOKEN"
openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ${KEYSTONE_ADMIN_PASSWORD}

echo "INFO: Kill /usr/bin/keystone-all"
kill -9 ${keystone_all_pid}
sleep 3
echo "INFO: Set openstack-keystone to start at boot"
chkconfig openstack-keystone on

echo "INFO: Ensure db is migrated to current keystone version"
/usr/bin/keystone-manage db_sync
/usr/bin/keystone-manage db_sync --extension spassword

