#!/bin/bash
echo "[ keystone-entrypoint - start ] "

# Check argument DB_HOST
DB_HOST_ARG=${1}
DB_HOST_VALUE=${2}

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    echo "[ keystone-entrypoint - sleep] "
    sleep 30
    echo "[ keystone-entrypoint - launch post config] "
    /opt/keystone/postlaunchconfig.sh $DB_HOST_ARG $DB_HOST_VALUE
fi

echo "[ keystone-entrypoint - keystone-all] "
keystone-all
