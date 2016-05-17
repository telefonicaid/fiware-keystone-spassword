#!/bin/bash
echo "[ keystone-entrypoint - starts... ] "

# Check argument DB_HOST
DB_HOST_ARG=${1}
DB_HOST_VALUE=${2}

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    sleep 40
    # Check if postlaunchconfig was executed
    chkconfig openstack-keystone --level 3
    if [ "$?" == "1" ]; then
        /opt/keystone/postlaunchconfig.sh $DB_HOST_ARG $DB_HOST_VALUE
    fi
fi

echo "[ keystone-entrypoint - keystone-all ] "
/usr/bin/keystone-all
