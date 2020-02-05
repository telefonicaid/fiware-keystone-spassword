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

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     database connection mysql://keystone:keystone@$DB_HOST_NAME:$DB_HOST_PORT/keystone;

fi


/usr/bin/keystone-wsgi-public --port 5001 &
keystone_all_pid=`ps -Af | grep keystone-wsgi-public | awk '{print $2}'`
/usr/bin/keystone-wsgi-admin --port 35357 &
keystone_admin_pid=`ps -Af | grep keystone-wsgi-admin | awk '{print $2}'`
sleep 5

if [ "$TOKEN_EXPIRATION_TIME_ARG" == "-token_expiration_time" ]; then
    TOKEN_EXPIRATION_TIME=$TOKEN_EXPIRATION_TIME_VALUE
    openstack-config --set /etc/keystone/keystone.conf \
                     token expiration $TOKEN_EXPIRATION_TIME
fi

export OS_SERVICE_TOKEN=ADMIN
export OS_SERVICE_ENDPOINT=http://127.0.0.1:35357/v2.0
export KEYSTONE_HOST="127.0.0.1:5001"


# Get Domain Admin Id form domain if Liberty or minor or project if Mitaka or uppper
ID_ADMIN_DOMAIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from project p where p.name="admin_domain";' | awk '{if ($2=="admin_domain") print $1}'`


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
     | .["identity:get_project_roles"]=""
     | .cloud_admin="rule:admin_required and domain_id:'${ID_ADMIN_DOMAIN}'"
     | .cloud_service="rule:service_role and domain_id:'${ID_ADMIN_DOMAIN}'"' \
  | tee /etc/keystone/policy.json

/usr/bin/keystone-manage db_sync

# Set another ADMIN TOKEN
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT admin_token $KEYSTONE_ADMIN_PASSWORD



IOTAGENT_ID=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="iotagent"' | awk '{if ($4=="iotagent") print $2}'`
NAGIOS_ID=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="nagios";' | awk '{if ($4=="nagios") print $2}'`
ID_CLOUD_ADMIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="cloud_admin"' | awk '{if ($4=="cloud_admin") print $2}'`
ID_CLOUD_SERVICE=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="pep"' | awk '{if ($4=="pep") print $2}'`



# Exclude some users from spassword
openstack-config --set /etc/keystone/keystone.conf \
                 spassword pwd_user_blacklist $ID_CLOUD_ADMIN,$ID_CLOUD_SERVICE,$NAGIOS_ID,$IOTAGENT_ID



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

# Ensure db is migrated to current keystone version
/usr/bin/keystone-manage db_sync


kill -9 $keystone_all_pid
kill -9 $keystone_admin_pid

