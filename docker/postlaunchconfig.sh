#!/bin/bash

echo "INFO: postlaunchconfig INI"

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

if [ "${DEFAULT_PASSWORD_ARG}" == "-default_pwd" ]; then
    KEYSTONE_ADMIN_PASSWORD=${DEFAULT_PASSWORD_VALUE}
fi

if [ "${MYSQL_PASSWORD_ARG}" == "-mysql_pwd" ]; then
    MYSQL_ROOT_PASSWORD="${MYSQL_PASSWORD_VALUE}"
fi

# Set admin token correctly before
openstack-config --set /etc/keystone/keystone.conf DEFAULT admin_token ${KEYSTONE_ADMIN_PASSWORD}

if [ "${DB_HOST_ARG}" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:${KEYSTONE_ADMIN_PASSWORD}@${DB_HOST_VALUE}/keystone
    # Ensure previous keystone database does not exist. Needed MySQL root access
    mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -uroot --password=${MYSQL_ROOT_PASSWORD} -e 'exit'
    if [ $? == 0 ]; then
        echo "INFO: You have MySQL root access. Try to drop keystone user and database and create new"
        mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -uroot --password=${MYSQL_ROOT_PASSWORD} <<EOF
DROP DATABASE keystone;
DROP USER 'keystone'@'%';
EOF
        mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -uroot --password=${MYSQL_ROOT_PASSWORD} <<EOF
CREATE DATABASE keystone;
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' IDENTIFIED BY '${KEYSTONE_ADMIN_PASSWORD}';
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' IDENTIFIED BY '${KEYSTONE_ADMIN_PASSWORD}';
EOF
    else
        echo "INFO: No access MySQL root access"
        # Check if you have a user and database created
        mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -ukeystone --password=${KEYSTONE_ADMIN_PASSWORD} -e 'use keystone'
        if [ $? == 0 ]; then
            echo "INFO: You have keystone MySQL database and user"
            # Check if keystone is installed
            mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -ukeystone --password=${KEYSTONE_ADMIN_PASSWORD} -e 'use keystone; select count(*) from user'
            if [ $? == 0 ]; then
                echo "ERROR: No access MySQL root access and keystone is installed. The keystone user and database should be deleted from MySQL database manually"
                exit 2
            else
                echo "INFO: Keystone is not installed"
            fi
        else
            echo "ERROR: You don't have keystone MySQL database and user and cannot create"
            exit 2
        fi
    fi

fi

echo "INFO: Launch /usr/bin/keystone-manage db_sync"
/usr/bin/keystone-manage db_sync
echo "INFO: Launch /usr/bin/keystone-manage db_sync --extension spassword"
/usr/bin/keystone-manage db_sync --extension spassword

echo "INFO: First start of /usr/bin/keystone-all"
/usr/bin/keystone-all &
keystone_all_pid=`echo $!`

# Keystone variables for command line use
export SERVICE_TOKEN=${KEYSTONE_ADMIN_PASSWORD}
export SERVICE_ENDPOINT=http://127.0.0.1:35357/v2.0
export KEYSTONE_HOST="127.0.0.1:5001"

echo "INFO: Wait until SERVICE_ENDPOINT is up or exit if timeout of <${DBTIMEOUT}>"
# Current time in seconds
STARTTIME=$(date +%s)
while ! tcping -q -t 1 127.0.0.1 35357
do
  [[ $(($(date +%s) - ${DBTIMEOUT})) -lt ${STARTTIME} ]] || { echo "ERROR: Timeout SERVICE_ENDPOINT <127.0.0.1:35357> Exceeds <${DBTIMEOUT}>" >&2; exit 3; }
  echo "INFO: Wait for SERVICE_ENDPOINT <${DB_HOST_NAME}:${DB_HOST_PORT}>"
  sleep 1
done
echo "INFO: It took $(($(date +%s) - ${STARTTIME})) seconds to startup"

echo "INFO: Create Services"

echo "INFO: Create user admin"
keystone user-create --name=admin --pass=${KEYSTONE_ADMIN_PASSWORD} --email=admin@no.com 
echo "INFO: Create role admin"
keystone role-create --name=admin
echo "INFO: Create tenant admin"
keystone tenant-create --name=admin --description="Admin Tenant"
echo "INFO: Add role admin to user admin and tenant admin"
keystone user-role-add --user=admin --tenant=admin --role=admin
echo "INFO: Create role service"
keystone role-create --name=service
echo "INFO: Create user iotagent"
keystone user-create --name=iotagent --pass=${KEYSTONE_ADMIN_PASSWORD} --email=iotagent@no.com
echo "INFO: Create user nagios"
keystone user-create --name=nagios --pass=${KEYSTONE_ADMIN_PASSWORD} --email=nagios@no.com
echo "INFO: Add role admin to user nagios and tenant admin"
keystone user-role-add --user=nagios --tenant=admin --role=admin

echo "INFO: Obtain user list and find iotagent user"
IOTAGENT_ID=`keystone user-list | grep "iotagent" | awk '{print $2}'`

ADMIN_TOKEN=$(\
curl http://${KEYSTONE_HOST}/v3/auth/tokens   \
         -s                                   \
         -i                                   \
         -H "Content-Type: application/json"  \
         -d '
     {
      "auth": {
          "identity": {
              "methods": [
                  "password"
              ],
              "password": {
                  "user": {
                      "domain": {
                          "name": "Default"
                      },
                      "name": "admin",
                      "password": "'${KEYSTONE_ADMIN_PASSWORD}'"
                  }
              }
          },
          "scope": {
              "project": {
                  "domain": {
                      "name": "Default"
                  },
                  "name": "admin"
              }
          }
      }
    }' | grep ^X-Subject-Token: | awk '{print $2}' )
echo "ADMIN_TOKEN: ${ADMIN_TOKEN}"

ID_ADMIN_DOMAIN=$(\
curl http://${KEYSTONE_HOST}/v3/domains     \
    -s                                      \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"       \
    -H "Content-Type: application/json"     \
    -d '
  {
      "domain": {
      "enabled": true,
      "name": "admin_domain"
      }
  }' | jq .domain.id | tr -d '"' )
echo "ID_ADMIN_DOMAIN: ${ID_ADMIN_DOMAIN}"

ID_CLOUD_SERVICE=$(\
curl http://${KEYSTONE_HOST}/v3/users       \
    -s                                      \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"       \
    -H "Content-Type: application/json"     \
    -d '
  {
      "user": {
          "description": "Cloud service",
          "domain_id": "'${ID_ADMIN_DOMAIN}'",
          "enabled": true,
          "name": "pep",
          "password": "'${KEYSTONE_ADMIN_PASSWORD}'"
      }
  }' | jq .user.id | tr -d '"' )
echo "ID_CLOUD_SERVICE: ${ID_CLOUD_SERVICE}"

ID_CLOUD_ADMIN=$(\
curl http://${KEYSTONE_HOST}/v3/users       \
    -s                                      \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"       \
    -H "Content-Type: application/json"     \
    -d '
  {
      "user": {
          "description": "Cloud administrator",
          "domain_id": "'${ID_ADMIN_DOMAIN}'",
          "enabled": true,
          "name": "cloud_admin",
          "password": "'${KEYSTONE_ADMIN_PASSWORD}'"
      }
  }' | jq .user.id | tr -d '"' )
echo "ID_CLOUD_ADMIN: ${ID_CLOUD_ADMIN}"

ADMIN_ROLE_ID=$(\
curl "http://${KEYSTONE_HOST}/v3/roles?name=admin" \
    -s                                             \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"              \
    | jq .roles[0].id | tr -d '"' )
echo "ADMIN_ROLE_ID: ${ADMIN_ROLE_ID}"

echo "INFO: Create domain admin_domain user cloud_admin role admin"
curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_ADMIN}/roles/${ADMIN_ROLE_ID} \
    -s                                   \
    -i                                   \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"    \
    -H "Content-Type: application/json"

SERVICE_ROLE_ID=$(\
curl "http://${KEYSTONE_HOST}/v3/roles?name=service" \
    -s                                               \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"                \
    | jq .roles[0].id | tr -d '"' )
echo "SERVICE_ROLE_ID: ${SERVICE_ROLE_ID}"

echo "INFO: Create domain admin_domain user pep role service"
curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_SERVICE}/roles/${SERVICE_ROLE_ID} \
    -s                                   \
    -i                                   \
    -H "X-Auth-Token: ${ADMIN_TOKEN}"    \
    -H "Content-Type: application/json"

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

echo "INFO: Set another ADMIN TOKEN"
openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ${KEYSTONE_ADMIN_PASSWORD}

echo "INFO: Exclude some users from spassword"
openstack-config --set /etc/keystone/keystone.conf \
    spassword pwd_user_blacklist ${ID_CLOUD_ADMIN},${ID_CLOUD_SERVICE},${IOTAGENT_ID}

echo "INFO: Kill /usr/bin/keystone-all"
kill -9 ${keystone_all_pid}
echo "INFO: Set openstack-keystone to start at boot"
chkconfig openstack-keystone on

