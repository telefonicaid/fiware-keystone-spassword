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
%define keystone_conf /etc/keystone/keystone.conf

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
  -e '/^\[pipeline:api_v3\]$/,/^\[/ s/^pipeline\(.*\) scim_extension service_v3$/pipeline\1 spassword_checker spassword_time scim_extension service_v3/' \
  -e 's/\[pipeline:api_v3\]/[filter:spassword_checker]\npaste.filter_factory = keystone_spassword.contrib.spassword.routers.PasswordExtension.factory\n\n&/' \
  -e 's/\[pipeline:api_v3\]/[filter:spassword_time]\npaste.filter_factory = keystone_spassword.contrib.spassword.PasswordMiddleware.factory\n\n&/' \
  %{keystone_paste}
else
  echo "SPASSWORD extension already configured. Skipping."
fi

if ! grep -q -F "password=keystone_spassword.contrib.spassword.SPassword" "%{keystone_conf}"; then
  echo "Adding new spassword plugin module."
  sed -i \
      -e 's/\#password=keystone.auth.plugins.password.Password$/password=keystone_spassword.contrib.spassword.SPassword\n&/' \
    %{keystone_conf}
else
  echo "Already installed spassword Password plugin module. Skipping."
fi

if ! grep -q -F "driver=keystone_spassword.contrib.spassword.backends.sql.Identity" "%{keystone_conf}"; then
  echo "Adding new spassword plugin module."
  sed -i \
      -e 's/\#driver=keystone.identity.backends.sql.Identity$/driver=keystone_spassword.contrib.spassword.backends.sql.Identity\n&/' \
    %{keystone_conf}
else
  echo "Already installed spassword Identity plugin module. Skipping."
fi

if ! grep -q -F "[spassword]" "%{keystone_conf}"; then
    echo "Adding spassword config "
    echo "[spassword]
enabled=false
smtp_server='0.0.0.0'
smtp_port=587
smtp_tls=True
smtp_user='smtpuser@yourdomain.com'
smtp_password='yourpasswrod'
smtp_from='smtpuser'
password_expiration_days=2*365/12 ">>  %{keystone_conf}

ln -fs %{_root}/keystone_spassword/contrib/spassword %{python_lib}/keystone/contrib
keystone-manage db_sync --extension password

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

if grep -q -F "[filter:spassword_checker]" "%{keystone_conf}"; then
  echo "Removing SPASSWORD password and identity plugin extensions from Keystone configuration."
  sed -i \
  -e 's/password=keystone_spassword.contrib.spassword.SPassword //g' \
  -e 's/driver=keystone_spassword.contrib.spassword.backends.sql.Identity //g' \
  %{keystone_conf}
else
  echo "SPASSWORD extension not configured. Skipping."
fi
