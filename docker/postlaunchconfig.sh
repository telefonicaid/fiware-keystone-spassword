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

TOKEN_EXPIRATION_TIME_ARG=${7}
TOKEN_EXPIRATION_TIME_VALUE=${8}

if [ "$DEFAULT_PASSWORD_ARG" == "-default_pwd" ]; then
    KEYSTONE_ADMIN_PASSWORD=$DEFAULT_PASSWORD_VALUE
fi

if [ "$MYSQL_PASSWORD_ARG" == "-mysql_pwd" ]; then
    MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD_VALUE"
fi


[[ "${SPASSWORD_ENABLED}" == "" ]] && export SPASSWORD_ENABLED=True
[[ "${SPASSWORD_PWD_MAX_TRIES}" == "" ]] && export SPASSWORD_PWD_MAX_TRIES=5
[[ "${SPASSWORD_PWD_BLOCK_MINUTES}" == "" ]] && export SPASSWORD_PWD_BLOCK_MINUTES=30
[[ "${SPASSWORD_PWD_EXP_DAYS}" == "" ]] && export SPASSWORD_PWD_EXP_DAYS=365
[[ "${SPASSWORD_SMTP_SERVER}" == "" ]] && export SPASSWORD_SMTP_SERVER='0.0.0.0'
[[ "${SPASSWORD_SMTP_PORT}" == "" ]] && export SPASSWORD_SMTP_PORT=587
[[ "${SPASSWORD_SMTP_TLS}" == "" ]] && export SPASSWORD_SMTP_TLS=True
[[ "${SPASSWORD_SMTP_USER}" == "" ]] && export SPASSWORD_SMTP_USER='smtpuser@yourdomain.com'
[[ "${SPASSWORD_SMTP_PASSWORD}" == "" ]] && export SPASSWORD_SMTP_PASSWORD='yourpassword'
[[ "${SPASSWORD_SMTP_FROM}" == "" ]] && export SPASSWORD_SMTP_FROM='smtpuser'
[[ "${SPASSWORD_SNDFA}" == "" ]] && export SPASSWORD_SNDFA=False
[[ "${SPASSWORD_SNDFA_ENDPOINT}" == "" ]] && export SPASSWORD_SNDFA_ENDPOINT='localhost:5001'
[[ "${SPASSWORD_SNDFA_TIME_WINDOW}" == "" ]] && export SPASSWORD_SNDFA_TIME_WINDOW=24

[[ "${LOG_LEVEL}" == "" ]] && export LOG_LEVEL=WARN


if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     database connection mysql+pymysql://keystone:keystone@$DB_HOST_NAME:$DB_HOST_PORT/keystone;
    # Ensure previous keystone database does not exist
    mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_ROOT_PASSWORD <<EOF
DROP DATABASE keystone;
EOF
    mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_ROOT_PASSWORD <<EOF
CREATE DATABASE keystone;
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' \
    IDENTIFIED BY 'keystone';
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' \
    IDENTIFIED BY 'keystone';
EOF

fi

if [ "$TOKEN_EXPIRATION_TIME_ARG" == "-token_expiration_time" ]; then
    if [ "${TOKEN_EXPIRATION_TIME}" == "" ]; then
        TOKEN_EXPIRATION_TIME=$TOKEN_EXPIRATION_TIME_VALUE
    fi
fi

if [ "${TOKEN_EXPIRATION_TIME}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     token expiration $TOKEN_EXPIRATION_TIME
fi

if [ "${REDIS_ENDPOINT}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    cache enabled true
    openstack-config --set /etc/keystone/keystone.conf \
    cache backend dogpile.cache.redis
    openstack-config --set /etc/keystone/keystone.conf \
    cache backend_argument url:redis://$REDIS_ENDPOINT
fi

if [ "${REVOKE_EXPIRATION_BUFFER}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    revoke expiration_buffer $REVOKE_EXPIRATION_BUFFER
fi

if [ "${LOG_LEVEL}" == "INFO" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT verbose True
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT debug False
fi

if [ "${LOG_LEVEL}" == "DEBUG" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT verbose True
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT debug True
fi

echo "[ postlaunchconfig - db_sync ] "
/usr/bin/keystone-manage db_sync

echo "[ postlaunchconfig - fernet_setup ] "
/usr/bin/keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone

echo "[ postlaunchconfig - bootstrap ] "
/usr/bin/keystone-manage bootstrap \
  --bootstrap-password $KEYSTONE_ADMIN_PASSWORD \
  --bootstrap-admin-url http://127.0.0.1:35357 \
  --bootstrap-public-url http://127.0.0.1:5001 \
  --bootstrap-internal-url http://127.0.0.1:35357 \
  --bootstrap-region-id RegionOne

echo "[ postlaunchconfig - Start UWSGI process ] "
/usr/bin/keystone-wsgi-public --port 5001 &
sleep 2
keystone_all_pid=`ps -Af | grep keystone-wsgi-public | awk '{print $2}'`
/usr/bin/keystone-wsgi-admin --port 35357 &
sleep 2
keystone_admin_pid=`ps -Af | grep keystone-wsgi-admin | awk '{print $2}'`
sleep 5



# Create Services
export KEYSTONE_HOST="127.0.0.1:5001"

export OS_USERNAME=admin
export OS_PASSWORD=$KEYSTONE_ADMIN_PASSWORD
export OS_PROJECT_NAME=admin
export OS_USER_DOMAIN_ID=default
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_ID=default
export OS_PROJECT_DOMAIN_NAME=Default
export OS_AUTH_URL=http://127.0.0.1:5001/v3
export OS_IDENTITY_API_VERSION=3

echo "[ postlaunchconfig - create roles  ] "
# openstack role create admin
openstack role add  --user admin --project admin admin
openstack role create service
echo "[ postlaunchconfig - delete roles  ] "
openstack role delete _member_
echo "[ postlaunchconfig - create users ] "
openstack user create --password $KEYSTONE_ADMIN_PASSWORD --email iotagent@no.com iotagent
openstack user create --password $KEYSTONE_ADMIN_PASSWORD --email nagios@no.com nagios
echo "[ postlaunchconfig - assign roles to users ] "
openstack role add --user nagios --project admin admin

echo "[ postlaunchconfig - list users ] "
IOTAGENT_ID=`openstack user list | grep "iotagent" | awk '{print $2}'`
NAGIOS_ID=`openstack user list | grep "nagios" | awk '{print $2}'`
echo "IOTAGENT_ID: $IOTAGENT_ID"
echo "NAGIOS_ID: $NAGIOS_ID"
[[ "${NAGIOS_ID}" == null ]] && exit 0
[[ "${NAGIOS_ID}" == "" ]] && exit 0

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
                      "password": "'$KEYSTONE_ADMIN_PASSWORD'"
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
echo "ADMIN_TOKEN: $ADMIN_TOKEN"
[[ "${ADMIN_TOKEN}" == "" ]] && exit 0

ID_ADMIN_DOMAIN=$(\
curl http://${KEYSTONE_HOST}/v3/domains          \
         -s                                      \
         -H "X-Auth-Token: $ADMIN_TOKEN"         \
         -H "Content-Type: application/json"     \
         -d '
  {
      "domain": {
      "enabled": true,
      "name": "admin_domain",
      "description": "admin_domain desc"
      }
  }' | jq .domain.id | tr -d '"' )
echo "ID_ADMIN_DOMAIN: $ID_ADMIN_DOMAIN"
ID_ADMIN_DOMAIN=`openstack domain list | grep "admin_domain" | awk '{print $2}'`
echo "ID_ADMIN_DOMAIN: $ID_ADMIN_DOMAIN"
[[ "${ID_ADMIN_DOMAIN}" == null ]] && exit 0

ID_CLOUD_SERVICE=$(\
curl http://${KEYSTONE_HOST}/v3/users             \
         -s                                       \
         -H "X-Auth-Token: $ADMIN_TOKEN"          \
         -H "Content-Type: application/json"      \
         -d '
  {
      "user": {
          "description": "Cloud service",
          "domain_id": "'$ID_ADMIN_DOMAIN'",
          "enabled": true,
          "name": "pep",
          "password": "'$KEYSTONE_ADMIN_PASSWORD'"
      }
  }' | jq .user.id | tr -d '"' )
echo "ID_CLOUD_SERVICE: $ID_CLOUD_SERVICE"

ID_CLOUD_ADMIN=$(\
curl http://${KEYSTONE_HOST}/v3/users              \
         -s                                        \
         -H "X-Auth-Token: $ADMIN_TOKEN"           \
         -H "Content-Type: application/json"       \
         -d '
  {
      "user": {
          "description": "Cloud administrator",
          "domain_id": "'$ID_ADMIN_DOMAIN'",
          "enabled": true,
          "name": "cloud_admin",
          "password": "'$KEYSTONE_ADMIN_PASSWORD'"
      }
  }' | jq .user.id | tr -d '"' )
echo "ID_CLOUD_ADMIN: $ID_CLOUD_ADMIN"

ADMIN_ROLE_ID=$(\
curl "http://${KEYSTONE_HOST}/v3/roles?name=admin"  \
         -s                                         \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
        | jq .roles[0].id | tr -d '"' )
echo "ADMIN_ROLE_ID: $ADMIN_ROLE_ID"

curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_ADMIN}/roles/${ADMIN_ROLE_ID} \
     -s                                 \
     -i                                 \
     -H "X-Auth-Token: $ADMIN_TOKEN"    \
     -H "Accept: application/json"      \
     -H "Content-Type: application/json"\
     -d '{ }'

SERVICE_ROLE_ID=$(\
curl "http://${KEYSTONE_HOST}/v3/roles?name=service" \
         -s                                          \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
        | jq .roles[0].id | tr -d '"' )
echo "SERVICE_ROLE_ID: $SERVICE_ROLE_ID"

curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_SERVICE}/roles/${SERVICE_ROLE_ID} \
      -s                                 \
      -i                                 \
      -H "X-Auth-Token: $ADMIN_TOKEN"    \
      -H "Accept: application/json"      \
      -H "Content-Type: application/json"\
      -d '{ }'

curl -s -L --insecure https://github.com/openstack/keystone/raw/queens-em/etc/policy.v3cloudsample.json \
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
     | .["identity:get_project_roles"]=""
     | .cloud_admin="rule:admin_required and domain_id:'${ID_ADMIN_DOMAIN}'"
     | .cloud_service="rule:service_role and domain_id:'${ID_ADMIN_DOMAIN}'"' \
  | tee /etc/keystone/policy.json

# Set another ADMIN TOKEN
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT admin_token $KEYSTONE_ADMIN_PASSWORD

# Exclude some users from spassword
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_user_blacklist $ID_CLOUD_ADMIN,$ID_CLOUD_SERVICE,$IOTAGENT_ID,$NAGIOS_ID

# Set default spassword config
openstack-config --set /etc/keystone/keystone.conf \
                 spassword enabled $SPASSWORD_ENABLED
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_max_tries $SPASSWORD_PWD_MAX_TRIES
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_block_minutes $SPASSWORD_PWD_BLOCK_MINUTES
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_exp_days $SPASSWORD_PWD_EXP_DAYS
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_server $SPASSWORD_SMTP_SERVER
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_port $SPASSWORD_SMTP_PORT
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_tls $SPASSWORD_SMTP_TLS
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_user $SPASSWORD_SMTP_USER
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_password $SPASSWORD_SMTP_PASSWORD
openstack-config --set /etc/keystone/keystone.conf \
                 spassword smtp_from $SPASSWORD_SMTP_FROM
openstack-config --set /etc/keystone/keystone.conf \
                 spassword sndfa $SPASSWORD_SNDFA
openstack-config --set /etc/keystone/keystone.conf \
                 spassword sndfa_endpoint $SPASSWORD_SNDFA_ENDPOINT
openstack-config --set /etc/keystone/keystone.conf \
                 spassword sndfa_time_window $SPASSWORD_SNDFA_TIME_WINDOW

kill -9 $keystone_all_pid
kill -9 $keystone_admin_pid
