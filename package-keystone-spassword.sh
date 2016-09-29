#!/bin/bash
#
# Packages Keystone SPASSWORD extension as RPM
#

BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source $BASE/get_version_string.sh
#read ver rel < <(get_rpm_version_string)
string=$(get_rpm_version_string)
VERSION_VALUE=${string% *}
RELEASE_VALUE=${string#* }

args=("$@")
ELEMENTS=${#args[@]}

for (( i=0;i<$ELEMENTS;i++)); do
    arg=${args[${i}]}
    if [ "$arg" == "with_python27" ]; then
        PYTHON27_VALUE=1
    fi
    if [ "$arg" == "with_version" ]; then
        VERSION_VALUE=${args[${i}+1]}
        RELEASE_VALUE=0
    fi
done

RPM_DIR=$BASE/build/rpm
mkdir -p $RPM_DIR/BUILD

rpmbuild -bb keystone-spassword.spec \
  --define "_topdir $RPM_DIR" \
  --define "_root $BASE"\
  --define "_version $VERSION_VALUE"\
  --define "_release $RELEASE_VALUE"\
  --define "with_python27 $PYTHON27_VALUE"
