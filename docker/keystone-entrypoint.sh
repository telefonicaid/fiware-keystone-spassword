#!/bin/bash
echo "[ keystone-entrypoint - starts... ] "

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

TOKEN_EXPIRATION_TIME_ARG=${7}
TOKEN_EXPIRATION_TIME_VALUE=${8}

[[ "${TOKEN_EXPIRATION_TIME_ARG}" == "" ]] && TOKEN_EXPIRATION_TIME_ARG="-token_expiration_time"
[[ "${TOKEN_EXPIRATION_TIME_VALUE}" == "" ]] && TOKEN_EXPIRATION_TIME_VALUE=10800  # 3 x 3600 seconds

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    # Wait until DB is up
    #while ! nc -z $DB_HOST_VALUE $DB_HOST_PORT ; do sleep 10; done
    while ! tcping -t 1 $DB_HOST_NAME $DB_HOST_PORT; do sleep 10; done
    # Check if postlaunchconfig was executed
    chkconfig openstack-keystone --level 3
    if [ "$?" == "1" ]; then
        # Check if previos DB data exists
        mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone'
        if [ "$?" == "1" ]; then
            /opt/keystone/postlaunchconfig.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $MYSQL_PASSWORD_ARG $MYSQL_PASSWORD_VALUE $TOKEN_EXPIRATION_TIME_ARG $TOKEN_EXPIRATION_TIME_VALUE
        else
            /opt/keystone/postlaunchconfig_update.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $MYSQL_PASSWORD_ARG $MYSQL_PASSWORD_VALUE $TOKEN_EXPIRATION_TIME_ARG $TOKEN_EXPIRATION_TIME_VALUE
        fi
    fi
fi

echo "[ keystone-entrypoint - keystone-all ] "
crond &
touch /var/log/keystone/keystone.log
chmod 666 /var/log/keystone/keystone.log
/usr/bin/keystone-all &
tail -f /var/log/keystone/keystone.log
