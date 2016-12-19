#!/bin/bash

KEYSTONE_ADMIN_PASSWORD=4pass1w0rd
MYSQL_ROOT_PASSWORD="iotonpremise"

DB_HOST_ARG=${1}
DB_HOST_VALUE=${2}

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
                     database connection mysql://keystone:keystone@$DB_HOST_VALUE/keystone;

fi

/usr/bin/keystone-all &
keystone_all_pid=`echo $!`
sleep 5    

# TODO: Get admin id

export OS_SERVICE_TOKEN=ADMIN
export OS_SERVICE_ENDPOINT=http://127.0.0.1:35357/v2.0
export KEYSTONE_HOST="127.0.0.1:5001"

ID_ADMIN_DOMAIN=`mysql -h $DB_HOST_VALUE -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from domain where name="admin_domain";' | awk '$2=="admin_domain" {print $1}'`

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
     | .["identity:list_role_assignments"]="rule:admin_on_domain_filter or rule:cloud_service or rule:admin_and_user_filter or rule:admin_and_project_filter"
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

# Ensure db is migrated to current keystone version
/usr/bin/keystone-manage db_sync
/usr/bin/keystone-manage db_sync --extension spassword
