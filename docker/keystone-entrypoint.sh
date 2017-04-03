#!/bin/bash

echo "INFO: keystone entrypoint start"

# Check argument DB_HOST
DB_HOST_ARG=${1}
# DB_HOST_VALUE can be hostname[:port]
DB_HOST_VALUE=${2}
DB_HOST_NAME="$(echo "${DB_HOST_VALUE}" | awk -F: '{print $1}')"
DB_HOST_PORT="$(echo "${DB_HOST_VALUE}" | awk -F: '{print $2}')"
# Default MySQL port 3306
[[ "${DB_HOST_PORT}" == "" ]] && DB_HOST_PORT=3306
# DBTIMEOUT in seconds. Default to 60 seconds
[[ "${DBTIMEOUT}" == "" ]] && export DBTIMEOUT=60

DEFAULT_PASSWORD_ARG=${3}
DEFAULT_PASSWORD_VALUE=${4}

MYSQL_PASSWORD_ARG=${5}
MYSQL_PASSWORD_VALUE=${6}

if [ "${DB_HOST_ARG}" == "-dbhost" ]; then
    echo "INFO: MySQL endpoint <${DB_HOST_VALUE}>"
    echo "INFO: DB_HOST_NAME <${DB_HOST_NAME}>"
    echo "INFO: DB_HOST_PORT <${DB_HOST_PORT}>"
    [[ "${DB_HOST_NAME}" == "" ]] && echo "ERROR: MySQL hostname not provided" >&2 && exit 2
    # Wait until DB is up or exit if timeout
    # Current time in seconds
    STARTTIME=$(date +%s)
    while ! tcping -t 1 ${DB_HOST_NAME} ${DB_HOST_PORT}
    do
        [[ $(($(date +%s) - ${DBTIMEOUT})) -lt ${STARTTIME} ]] || { echo "ERROR: Timeout MySQL endpoint <${DB_HOST_NAME}:${DB_HOST_PORT}>" >&2; exit 3; }
        echo "INFO: Wait for MySQL endpoint <${DB_HOST_NAME}:${DB_HOST_PORT}>"
        sleep 2
    done

    # Check if postlaunchconfig was executed
    chkconfig openstack-keystone --level 3
    if [ "$?" == "1" ]; then
        # Check if previous DB data exists
        mysql -s -h ${DB_HOST_NAME} -P ${DB_HOST_PORT} -uroot --password=${MYSQL_PASSWORD_VALUE} -e 'use keystone'
        if [ "$?" == "1" ]; then
            /opt/keystone/postlaunchconfig.sh ${DB_HOST_ARG} ${DB_HOST_VALUE} ${DEFAULT_PASSWORD_ARG} ${DEFAULT_PASSWORD_VALUE} ${MYSQL_PASSWORD_ARG} ${MYSQL_PASSWORD_VALUE}
        else
            /opt/keystone/postlaunchconfig_update.sh ${DB_HOST_ARG} ${DB_HOST_VALUE} ${DEFAULT_PASSWORD_ARG} ${DEFAULT_PASSWORD_VALUE} ${MYSQL_PASSWORD_ARG} ${MYSQL_PASSWORD_VALUE}
        fi
    fi
fi

echo "INFO: keystone entrypoint - keystone-all"
/usr/bin/keystone-all &
tail -f /var/log/keystone/keystone.log
