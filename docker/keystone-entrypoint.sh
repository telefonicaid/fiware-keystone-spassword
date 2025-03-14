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

DB_PASSWORD_ARG=${5}
DB_PASSWORD_VALUE=${6}

TOKEN_EXPIRATION_TIME_ARG=${7}
TOKEN_EXPIRATION_TIME_VALUE=${8}

[[ "${TOKEN_EXPIRATION_TIME_ARG}" == "" ]] && TOKEN_EXPIRATION_TIME_ARG="-token_expiration_time"
[[ "${TOKEN_EXPIRATION_TIME_VALUE}" == "" ]] && TOKEN_EXPIRATION_TIME_VALUE=10800  # 3 x 3600 seconds

if [ "$DB_PASSWORD_ARG" == "-mysql_pwd" ]; then
    DB_READY="mysqladmin ping -s --connect-timeout=3 -h $DB_HOST_NAME -P $DB_HOST_PORT"
    DB_LIST="mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$DB_PASSWORD_VALUE -e 'show databases'"
    DB_USE="mysql -h $DB_HOST_NAME --port $DB_HOST_PORT -u root --password=$DB_PASSWORD_VALUE -e 'use keystone'"
fi

if [ "$DB_PASSWORD_ARG" == "-psql_pwd" ]; then
    READY="pg_isready -h $DB_HOST_NAME -p $DB_HOST_PORT -t 3"
    DB_LIST="PGPASSWORD=$DB_PASSWORD_VALUE psql -h $DB_HOST_NAME -p $DB_HOST_PORT -U root -c '\l'"
    DB_USE="PGPASSWORD=$DB_PASSWORD_VALUE psql -h $DB_HOST_NAME -p $DB_HOST_PORT -U root -d keystone -c 'SELECT 1'"
fi

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    # Wait until DB is up, even if DB is behind a load balancer
    while ! eval $DB_READY; do sleep 10; done
    # Check if postlaunchconfig was executed
    chkconfig openstack-keystone --level 3
    if [ "$?" == "1" ]; then
        # Check if credentials are OK
        eval $DB_LIST
        if [ "$?" == "1" ]; then
            echo "[ keystone-entrypoint - error in mysql credentials ] Keystone docker will be not configured"
            exit 1
        fi
        # Check if previos DB data exists
        eval $DB_USE
        if [ "$?" == "1" ]; then
            rm -f /var/log/keystone/keystone.log
            /opt/keystone/postlaunchconfig.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $DB_PASSWORD_ARG $DB_PASSWORD_VALUE $TOKEN_EXPIRATION_TIME_ARG $TOKEN_EXPIRATION_TIME_VALUE
        else
            rm -f /var/log/keystone/keystone.log
            /opt/keystone/postlaunchconfig_update.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $DB_PASSWORD_ARG $DB_PASSWORD_VALUE $TOKEN_EXPIRATION_TIME_ARG $TOKEN_EXPIRATION_TIME_VALUE
        fi
    fi
fi

echo "[ keystone-entrypoint - crond ] "
crond &
echo "[keystone-entrypoint spassword config]"
tail -17 /etc/keystone/keystone.conf
touch /var/log/keystone/keystone.log
chmod 777 /var/log/keystone/
chmod 777 /var/log/keystone/keystone.log
echo "[ keystone-entrypoint - keystone-all ] "
/usr/bin/keystone-all &
sleep 5
rm -f /var/log/keystone/keystone.log
ln -snf /dev/stdout /var/log/keystone/keystone.log

sleep infinity


