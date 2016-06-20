#!/bin/bash
echo "[ keystone-entrypoint - starts... ] "

# Check argument DB_HOST
DB_HOST_ARG=${1}
DB_HOST_VALUE=${2}
DB_HOST_PORT=3306

DEFAULT_PASSWORD_ARG=${3}
DEFAULT_PASSWORD_VALUE=${4}

MYSQL_PASSWORD_ARG=${5}
MYSQL_PASSWORD_VALUE=${6}

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    # Wait until DB is up
    while ! nc -z $DB_HOST_VALUE $DB_HOST_PORT ; do sleep 10; done
    # Check if postlaunchconfig was executed
    chkconfig openstack-keystone --level 3
    if [ "$?" == "1" ]; then
        # Check if previos DB data exists
        mysql -u root --password=$MYSQL_PASSWORD_VALUE -e 'use keystone'
        if [ "$?" == "1" ]; then
            /opt/keystone/postlaunchconfig.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $MYSQL_PASSWORD_ARG $MYSQL_PASSWORD_VALUE
        else
            /opt/keystone/postlaunchconfig_update.sh $DB_HOST_ARG $DB_HOST_VALUE $DEFAULT_PASSWORD_ARG $DEFAULT_PASSWORD_VALUE $MYSQL_PASSWORD_ARG $MYSQL_PASSWORD_VALUE
        fi
    fi
fi

echo "[ keystone-entrypoint - keystone-all ] "
/usr/bin/keystone-all
