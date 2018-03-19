%define timestamp %(date +"%Y%m%d%H%M%S")
Name: keystone-spassword
Version: %{_version}
Release: %{_release}
Summary: Keystone SPASSWORD extension
License: Copyright 2015 Telefonica Investigación y Desarrollo, S.A.U
Distribution: noarch
Vendor: Telefonica I+D
Group: Applications/System
Packager: Telefonica I+D
Requires: openstack-keystone keystone-scim cracklib cracklib-python
autoprov: no
autoreq: no
Prefix: /opt
BuildArch: noarch

%define _target_os Linux
%define python_lib /usr/lib/python2.6/site-packages
%if 0%{?with_python27}
%define python_lib /usr/lib/python2.7/site-packages
%endif # if with_python27

%define check_paste %(test -e /etc/keystone/keystone-paste.ini && echo 1 || echo 0)
%if %{check_paste}
%define keystone_paste /etc/keystone/keystone-paste.ini
%else
%define keystone_paste /usr/share/keystone/keystone-dist-paste.ini
%endif

%define keystone_policy /etc/keystone/policy.json
%define keystone_conf /etc/keystone/keystone.conf

%description
SPASSWORD (System for ensure Strong passwords) extension for Keystone


%install
mkdir -p $RPM_BUILD_ROOT/%{python_lib}
cp -a %{_root}/keystone_spassword $RPM_BUILD_ROOT/%{python_lib}
find $RPM_BUILD_ROOT/%{python_lib}/keystone_spassword -name "*.pyc" -delete

%files
%defattr(644,root,root,755)
%{python_lib}/keystone_spassword/*

%post
if ! grep -q -F "[filter:spassword_checker]" "%{keystone_paste}"; then
  echo "Adding SPASSWORD extension to Keystone configuration."
  sed -i \
  -e '/^\[pipeline:api_v3\]$/,/^\[/ s/^pipeline\(.*\) scim_extension service_v3$/pipeline\1 spassword_checker scim_extension service_v3/' \
  -e 's/\[pipeline:api_v3\]/[filter:spassword_checker]\npaste.filter_factory = keystone_spassword.contrib.spassword.routers:SPasswordExtension.factory\n\n&/' \
  %{keystone_paste}
else
  echo "SPASSWORD extension already configured. Skipping."
fi

openstack-config --set /etc/keystone/keystone.conf \
                 auth password keystone_spassword.contrib.spassword.SPassword

openstack-config --set /etc/keystone/keystone.conf \
                 identity driver keystone_spassword.contrib.spassword.backends.sql.Identity

if ! grep -q -F "[spassword]" "%{keystone_conf}"; then
    echo "Adding spassword config "
    echo "
[spassword]
enabled=true
pwd_max_tries=5
pwd_block_minutes=30
pwd_exp_days=365
pwd_user_blacklist=
smtp_server='0.0.0.0'
smtp_port=587
smtp_tls=true
smtp_user='smtpuser@yourdomain.com'
smtp_password='yourpassword'
smtp_from='smtpuser'
sndfa=true
sndfa_endpoint='localhost:5001'
sndfa_time_window=24
">> %{keystone_conf}
fi

ln -fs %{python_lib}/keystone_spassword/contrib/spassword %{python_lib}/keystone/contrib
keystone-manage db_sync --extension spassword

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
  -e 's/spassword_checker //g' \
  %{keystone_paste}
else
  echo "SPASSWORD extension not configured. Skipping."
fi

if grep -q -F "[filter:spassword_checker]" "%{keystone_conf}"; then
  echo "Removing SPASSWORD password and identity plugin extensions from Keystone configuration."
  sed -i \
  -e 's/password=keystone_spassword.contrib.spassword.SPassword//g' \
  -e 's/driver=keystone_spassword.contrib.spassword.backends.sql.Identity//g' \
  %{keystone_conf}
else
  echo "SPASSWORD extension not configured. Skipping."
fi
