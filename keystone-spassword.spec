%define timestamp %(date +"%Y%m%d%H%M%S")
Name: keystone-spassword
Version: 0.1.0
Release: %{timestamp}
Summary: Keystone SPASSWORD extension
License: Copyright 2015 Telefonica Investigación y Desarrollo, S.A.U
Distribution: noarch
Vendor: Telefonica I+D
Group: Applications/System
Packager: Telefonica I+D
Requires: openstack-keystone keystone-scim
autoprov: no
autoreq: no
Prefix: /opt
BuildArch: noarch

%define _target_os Linux
%define python_lib /usr/lib/python2.6/site-packages
%define keystone_paste /usr/share/keystone/keystone-dist-paste.ini
%define keystone_policy /etc/keystone/policy.json

%description
SPASSWORD (System for ensure Strong passwords) extension for Keystone


%install
mkdir -p $RPM_BUILD_ROOT/%{python_lib}
cp -a %{_root}/keystone_spassword $RPM_BUILD_ROOT/%{python_lib}
find $RPM_BUILD_ROOT/%{python_lib}/keystone_spassword -name "*.pyc" -delete

%files
"/usr/lib/python2.6/site-packages/keystone_spassword"

%post
if ! grep -q -F "[filter:spassword_checker]" "%{keystone_paste}"; then
  echo "Adding SPASSWORD extension to Keystone configuration."
  sed -i \
  -e '/^\[pipeline:api_v3\]$/,/^\[/ s/^pipeline\(.*\) service_v3$/pipeline\1 spassword_checker spassword_time scim__extension service_v3/' \
  -e 's/\[pipeline:api_v3\]/[filter:spassword_checker]\npaste.filter_factory = keystone_spassword.contrib.spassword.PasswordExtension.factory\n\n&/' \
  -e 's/\[pipeline:api_v3\]/[filter:spassword_time]\npaste.filter_factory = keystone_spassword.contrib.spassword.PasswordMiddleware.factory\n\n&/' \  
  %{keystone_paste}
else
  echo "SPASSWORD extension already configured. Skipping."
fi


echo "SPASSWORD extension installed successfully. Restart Keystone daemon to take effect."

%preun
if [ $1 -gt 0 ] ; then
  # upgrading: no remove extension
  exit 0
fi
if grep -q -F "[filter:spassword_checker]" "%{keystone_paste}"; then
  echo "Removing SPASSWORD extension from Keystone configuration."
  sed -i \
      -e "/\[filter:spassword_checker\]/,+2 d" \
      -e "/\[filter:spassword_time\]/,+2 d" \      
  -e 's/spassword_checker //g' \
  -e 's/spassword_time //g' \     
  %{keystone_paste}
else
  echo "SPASSWORD extension not configured. Skipping."
fi
