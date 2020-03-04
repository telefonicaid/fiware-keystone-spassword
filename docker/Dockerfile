FROM centos:centos7

MAINTAINER IoT team

ENV DB_HOST localhost
ENV KEYSTONE_ADMIN_PASSWORD 4pass1w0rd
ENV KEYSTONE_SCIM_VERSION 1.3.0
ENV KEYSTONE_SPASSWORD_VERSION 1.6.0

COPY ./*.sh /opt/keystone/
COPY ./sql_ldap.py /opt/keystone/
COPY ./*.patch /opt/keystone/
COPY ./keystone-all /opt/keystone/

WORKDIR /opt/keystone

RUN \
    # Install dependencies
    yum update -y && yum install -y curl && \
    yum install -y epel-release && yum update -y epel-release && \
    # Install MySQL client
    yum -y install mysql git && \
    # Install keystone dependencies
    yum -y install rpm-build tar findutils && \
    yum -y install python cronie && \
    curl -s --insecure -L 'https://repos.fedorapeople.org/openstack/EOL/openstack-ocata/rdo-release-ocata-3.noarch.rpm?raw=true' > rdo-release-ocata-3.noarch.rpm && \
    yum localinstall -y --nogpgcheck rdo-release-ocata-3.noarch.rpm && \
    # Set Centos mirror to ensure openstack version
    sed -i 's/http:\/\/mirror.centos.org/https:\/\/buildlogs.centos.org/g' /etc/yum.repos.d/rdo-release.repo && \
    sed -i 's/gpgcheck=1/gpgcheck=0/g' /etc/yum.repos.d/rdo-release.repo && \
    # Install keystone dependencies
    yum -y install openstack-utils openstack-keystone python-keystoneclient  && \
    yum -y install python-openstackclient && \
    yum -y install httpd mod_wsgi && \
    # https://docs.openstack.org/ocata/install-guide-rdo/keystone-install.html
    sed -i 's/#ServerName www.example.com:80/ServerName 127.0.0.1 /g' /etc/httpd/conf/httpd.conf && \
    sed -i 's/5000/5001/g' /usr/share/keystone/wsgi-keystone.conf && \
    ln -s /usr/share/keystone/wsgi-keystone.conf /etc/httpd/conf.d && \
    systemctl enable httpd.service && \
    cp /opt/keystone/keystone-all /usr/bin && \
    chmod 755 /usr/bin/keystone-all && \
    yum -y install unzip tcping jq python2-redis && \
    yum -y install cracklib cracklib-python && \
    # Set keystone configuration
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001  && \
    openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true  && \
    openstack-config --set /etc/keystone/keystone.conf \
    token provider uuid && \
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql+pymysql://keystone:keystone@$DB_HOST/keystone && \
    # Set keystone SSL configuration
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone  && \
    chown -R keystone:keystone /etc/keystone/ssl && \
    chmod -R o-rwx /etc/keystone/ssl && \
    # Create /opt/keystone
    mkdir -p /opt/keystone && \
    # Keystone postconfig file
    chmod 755 /opt/keystone/postlaunchconfig.sh /opt/keystone/postlaunchconfig_update.sh /opt/keystone/keystone-entrypoint.sh && \
    ln -s /etc/keystone/keystone-paste.ini /usr/share/keystone/keystone-dist-paste.ini && \
    # Install Keystone-SCIM
    tag=$KEYSTONE_SCIM_VERSION && \
    user="telefonicaid" && \
    repo_scim="fiware-keystone-scim" && \
    pack_scim="package-keystone-scim.sh" && \
    url_scim="https://github.com/${user}/${repo_scim}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_scim}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_scim}-${tag} && \
    source ./${pack_scim} --with-python27 --with-version $KEYSTONE_SCIM_VERSION --with-release 0 && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # Install Keystone-SPASSWORD
    cd /opt/keystone && \
    tag=$KEYSTONE_SPASSWORD_VERSION && \
    user="telefonicaid" && \
    repo_spassword="fiware-keystone-spassword" && \
    pack_spassword="package-keystone-spassword.sh" && \
    url_spassword="https://github.com/${user}/${repo_spassword}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_spassword}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_spassword}-${tag} && \
    source ./${pack_spassword} --with-python27 --with-version $KEYSTONE_SPASSWORD_VERSION --with-release 0 && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # LDAP pre-support
    mkdir -p /etc/keystone/domains && \
    chown keystone.keystone /etc/keystone/domains && \
    openstack-config --set /etc/keystone/keystone.conf \
    identity domain_specific_drivers_enabled true && \
    openstack-config --set /etc/keystone/keystone.conf \
    identity domain_config_dir /etc/keystone/domains && \
    cp /opt/keystone/sql_ldap.py /usr/lib/python2.7/site-packages/keystone/identity/mapping_backends && \
    openstack-config --set /etc/keystone/keystone.conf \
    identity_mapping driver keystone.identity.mapping_backends.sql_ldap.Mapping && \
    # Patching ...
    cd /usr/lib/python2.7/site-packages/keystone/token/providers && \
    patch -f -p0 < /opt/keystone/common.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/identity && \
    patch -f -p0 < /opt/keystone/core.patch && \
    find /usr/lib/python2.7/site-packages/keystone -name "*.pyc" -delete && \
    find /usr/lib/python2.7/site-packages/keystone -name "*.pyo" -delete && \
    # Cron task for remove expired tokens
    echo "0 */1 * * * root /usr/bin/keystone-manage token_flush" >/etc/cron.d/tokenflush && \
    # Cleaning unused files...
    rpm -e --nodeps redhat-logos || true && yum -y erase libss && \
    yum clean all && rm -rf /var/lib/yum/yumdb && \
    rm -rf /var/lib/yum/history && find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en' ! -name 'es' ! -name 'es_ES' | xargs rm -r && \
    rm -rf ~/fiware-keystone && rm -f /var/log/*log && rm -f /opt/keystone/*.rpm


# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]


EXPOSE 5001 35357

