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
[[ "${ROTATE_FERNET_KEYS}" == "" ]] && export ROTATE_FERNET_KEYS=True

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     database connection mysql+pymysql://keystone:keystone@$DB_HOST_NAME:$DB_HOST_PORT/keystone;

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
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT insecure_debug True
    openstack-config --set /etc/keystone/keystone.conf \
    wsgi debug_middleware True
fi

if [ "${ROTATE_FERNET_KEYS}" == "True" ]; then
    # Cron task to rotate fernet tokens once a day
    echo "0 1 * * * root /usr/bin/keystone-manage fernet_rotate --keystone-user keystone --keystone-group keystone" >/etc/cron.d/fernetrotate
fi

if [ "${SAML_ENDPOINT}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     saml idp_entity_id https://$SAML_ENDPOINT/v3/OS-FEDERATION/saml2/idp
    openstack-config --set /etc/keystone/keystone.conf \
                     saml idp_sso_endpoint https://$SAML_ENDPOINT/v3/OS-FEDERATION/saml2/idp
fi
if [ "${SAML_CERTFILE}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     saml certfile $SAML_CERTFILE
fi
if [ "${SAML_KEYFILE}" != "" ]; then
    openstack-config --set /etc/keystone/keystone.conf \
                     saml keyfile $SAML_KEYFILE
fi


export KEYSTONE_HOST="127.0.0.1:5001"

echo "[ postlaunchconfig_update - Start UWSGI process ] "
/usr/bin/keystone-all &
sleep 5


# Get Domain Admin Id form domain if Liberty or minor or project if Mitaka or uppper
ID_ADMIN_DOMAIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from project p where p.name="admin_domain";' | awk '{if ($2=="admin_domain") print $1}'`
echo "ID_ADMIN_DOMAIN: $ID_ADMIN_DOMAIN"
[[ "${ID_ADMIN_DOMAIN}" == null ]] && exit 0
[[ "${ID_ADMIN_DOMAIN}" == "" ]] && exit 0

cat /opt/keystone/policy.v3cloudsample.json \
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
     | .["identity:get_user"]="rule:cloud_admin or rule:admin_and_matching_target_user_domain_id or rule:owner"
     | .["identity:list_users"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:create_user"]="rule:cloud_admin or rule:admin_and_matching_user_domain_id"
     | .["identity:update_user"]="rule:cloud_admin or rule:admin_and_matching_target_user_domain_id or rule:owner"
     | .["identity:delete_user"]="rule:cloud_admin or rule:admin_and_matching_target_user_domain_id"
     | .["identity:get_group"]="rule:cloud_admin or rule:admin_and_matching_target_group_domain_id"
     | .["identity:list_groups"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:list_groups_for_user"]="rule:owner or rule:admin_and_matching_target_user_domain_id"
     | .["identity:create_group"]="rule:cloud_admin or rule:admin_and_matching_group_domain_id"
     | .["identity:update_group"]="rule:cloud_admin or rule:admin_and_matching_target_group_domain_id"
     | .["identity:delete_group"]="rule:cloud_admin or rule:admin_and_matching_target_group_domain_id"
     | .["identity:list_users_in_group"]="rule:cloud_admin or rule:admin_and_matching_target_group_domain_id"
     | .["identity:get_role"]="rule:admin_required"
     | .["identity:list_roles"]="rule:admin_required"
     | .["identity:create_role"]="rule:admin_required"
     | .["identity:update_role"]="rule:admin_required"
     | .["identity:delete_role"]="rule:admin_required"
     | .["identity:list_domains"]="rule:cloud_admin or rule:cloud_service"
     | .cloud_admin="rule:admin_required and domain_id:'${ID_ADMIN_DOMAIN}'"
     | .cloud_service="rule:service_role and domain_id:'${ID_ADMIN_DOMAIN}'"' \
  | tee /etc/keystone/policy.json

echo "[ postlaunchconfig_update - db_sync ] "
/usr/bin/keystone-manage db_sync

# Ensure directory /etc/keystone/fernet-keys to be configured as volume
echo "[ postlaunchconfig_update - fernet_setup ] "
chown -R keystone:keystone /etc/keystone/fernet-keys
chmod -R o-rwx /etc/keystone/fernet-keys
/usr/bin/keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone

# Create metadata for your keystone IdP
if [ "${SAML_ENDPOINT}" != "" ] && [ "${SAML_CERTFILE}" != "" ] && [ "${SAML_KEYFILE}" != "" ]; then
    echo "[ postlaunchconfig_update - sml2_idp_metadata ] "
    openstack-config --set /etc/keystone/keystone.conf saml idp_metadata_path /etc/keystone/saml2_idp_metadata.xml
    /usr/bin/keystone-manage saml_idp_metadata > /etc/keystone/saml2_idp_metadata.xml
fi

# Set another ADMIN TOKEN
openstack-config --set /etc/keystone/keystone.conf \
                 DEFAULT admin_token $KEYSTONE_ADMIN_PASSWORD



IOTAGENT_ID=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="iotagent"' | awk '{if ($4=="iotagent") print $2}'`
NAGIOS_ID=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="nagios";' | awk '{if ($4=="nagios") print $2}'`
ID_CLOUD_ADMIN=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="cloud_admin"' | awk '{if ($4=="cloud_admin") print $2}'`
ID_CLOUD_SERVICE=`mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone; select * from local_user u where u.name="pep"' | awk '{if ($4=="pep") print $2}'`
echo "IOTAGENT_ID: $IOTAGENT_ID"
echo "NAGIOS_ID: $NAGIOS_ID"
echo "ID_CLOUD_ADMIN: $ID_CLOUD_ADMIN"
echo "ID_CLOUD_SERVICE: $ID_CLOUD_SERVICE"

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




# Ensure db is migrated to current keystone version
echo "[ postlaunchconfig_update - db_sync --migrate ] "
/usr/bin/keystone-manage db_sync --migrate

