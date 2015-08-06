#!/bin/sh
#
# Packages Keystone SPASSWORD extension as RPM
#

BASE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

RPM_DIR=$BASE/build/rpm
mkdir -p $RPM_DIR/BUILD

rpmbuild -bb keystone-spassword.spec \
  --define "_topdir $RPM_DIR" \
  --define "_root $BASE"
