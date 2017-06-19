FROM centos:7

MAINTAINER IoT team

# DB_ENDPOINT host[:port]
ENV DB_ENDPOINT localhost
ENV KEYSTONE_ADMIN_PASSWORD=
ENV KEYSTONE_SCIM_VERSION 1.1.7
ENV KEYSTONE_SPASSWORD_VERSION 1.2.0

COPY ./*.sh /opt/keystone/

WORKDIR /opt/keystone

RUN \
    # Install dependencies
    yum update -y && yum install -y curl && \
    yum install -y epel-release && yum update -y epel-release && \
    # yum plugins
    yum install -y yum-plugin-remove-with-leaves && \
    # Install MySQL client
    yum -y install mysql && \
    # Install rpm tools and python
    yum -y install rpm-build tar findutils && \
    yum -y install python python27  && \
    curl -s --insecure -L 'https://repos.fedorapeople.org/openstack/EOL/openstack-liberty/rdo-release-liberty-5.noarch.rpm?raw=true' > rdo-release-liberty-5.noarch.rpm && \
    yum localinstall -y --nogpgcheck rdo-release-liberty-5.noarch.rpm && \
    # Install keystone dependencies
    yum -y install openstack-utils openstack-keystone python-keystoneclient  && \
    yum -y install unzip tcping jq  && \
    yum -y install cracklib cracklib-python && \
    [[ "${KEYSTONE_ADMIN_PASSWORD}" == "" ]] && export KEYSTONE_ADMIN_PASSWORD=keystone && \
    # Set keystone configuration
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:${KEYSTONE_ADMIN_PASSWORD}@db/keystone && \
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ADMIN  && \
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001  && \
    openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true  && \
    openstack-config --set /etc/keystone/keystone.conf \
    token provider keystone.token.providers.uuid.Provider && \
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:${KEYSTONE_ADMIN_PASSWORD}@${DB_ENDPOINT}/keystone && \
    # Set keystone SSL configuration
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone  && \
    chown -R keystone:keystone /etc/keystone/ssl && \
    chmod -R o-rwx /etc/keystone/ssl && \
    # Create /opt/keystone
    mkdir -p /opt/keystone && \
    # Keystone postconfig file
    chmod 755 /opt/keystone/postlaunchconfig.sh /opt/keystone/postlaunchconfig_update.sh /opt/keystone/keystone-entrypoint.sh && \
    # Install Keystone-SCIM
    tag=${KEYSTONE_SCIM_VERSION} && \
    user="telefonicaid" && \
    repo_scim="fiware-keystone-scim" && \
    pack_scim="package-keystone-scim.sh" && \
    url_scim="https://github.com/${user}/${repo_scim}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_scim}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_scim}-${tag} && \
    source ./${pack_scim} --with-python27 --with-version ${KEYSTONE_SCIM_VERSION} && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # Install Keystone-SPASSWORD
    cd /opt/keystone && \
    tag=${KEYSTONE_SPASSWORD_VERSION} && \
    user="telefonicaid" && \
    repo_spassword="fiware-keystone-spassword" && \
    pack_spassword="package-keystone-spassword.sh" && \
    url_spassword="https://github.com/${user}/${repo_spassword}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_spassword}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_spassword}-${tag} && \
    source ./${pack_spassword} --with-python27 --with-version ${KEYSTONE_SPASSWORD_VERSION} && \
    rm -f docker/*.rpm && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # Cleaning unused files...
    yum -y erase libss && \
    yum -y erase --remove-leaves rpm-build && \
    # Clean yum data
    yum clean all && rm -rf /var/lib/yum/yumdb && rm -rf /var/lib/yum/history && \
    # Erase without dependencies unneded rpm packages
    rpm -qa redhat-logos | xargs -r rpm -e --nodeps && \
    # Rebuild rpm data files
    rpm --rebuilddb && \
    # Delete unused locales. Only preserve en_US and the locale aliases
    find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en_US' ! -name 'locale.alias' | xargs -r rm -r && \
    bash -c 'localedef --list-archive | grep -v -e "en_US" | xargs localedef --delete-from-archive' && \
    # We use cp instead of mv as to refresh locale changes for ssh connections
    # We use /bin/cp instead of cp to avoid any alias substitution, which in some cases has been problematic
    /bin/cp -f /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive.tmpl && \
    build-locale-archive && \
    # Don't need glibc locale data
    # This cannot be removed using yum as yum uses hard dependencies and doing so will uninstall essential packages
    rm -rf /usr/share/i18n /usr/{lib,lib64}/gconv && \
    # Don't need wallpapers
    rm -rf /usr/share/wallpapers/* && \
    # Don't need fiware-keystone repo files
    rm -rf ~/fiware-keystone && \
    # Don't need old log files inside docker images
    rm -rf /root/*log* /tmp/* /var/log/*log*

# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]

EXPOSE 5001

