#!/bin/bash

# Check argument DB_HOST
DB_HOST_ARG=${1}
DB_HOST_VALUE=${2}

if [ "$DB_HOST_ARG" == "-dbhost" ]; then
    sleep 30
    /opt/keystone/postlaunchconfig.sh $DB_HOST_ARGS $DB_HOST_VALUE
fi

keystone-all
