FROM centos:7.7.1908

MAINTAINER IoT team

ENV DB_HOST localhost
ENV KEYSTONE_ADMIN_PASSWORD 4pass1w0rd
ENV KEYSTONE_SCIM_VERSION 1.4.0
ENV KEYSTONE_SPASSWORD_VERSION 1.9.0

COPY ./*.sh /opt/keystone/
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
    curl -s --insecure -L 'https://repos.fedorapeople.org/openstack/openstack-rocky/rdo-release-rocky-2.noarch.rpm' > rdo-release-rocky-2.noarch.rpm && \
    yum localinstall -y --nogpgcheck rdo-release-rocky-2.noarch.rpm && \
    # Set Centos mirror to ensure openstack version
    sed -i 's/http:\/\/mirror.centos.org/https:\/\/buildlogs.centos.org/g' /etc/yum.repos.d/rdo-release.repo && \
    sed -i 's/gpgcheck=1/gpgcheck=0/g' /etc/yum.repos.d/rdo-release.repo && \
    # Install keystone dependencies
    yum -y install openstack-utils openstack-keystone python-keystoneclient  && \
    yum -y install python-openstackclient && \
    yum -y install httpd mod_wsgi && \
    # https://docs.openstack.org/keystone/queens/install/
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
    database connection mysql+pymysql://keystone:keystone@$DB_HOST/keystone && \
    # Set keystone Fernet tokens
    openstack-config --set /etc/keystone/keystone.conf \
    token provider fernet && \
    mkdir -p /etc/keystone/fernet-keys && \
    chown -R keystone:keystone /etc/keystone/fernet-keys && \
    chmod -R o-rwx /etc/keystone/fernet-keys && \
    keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone  && \
    openstack-config --set /etc/keystone/keystone.conf \
    fernet_tokens max_active_keys 6 && \
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
    # Patching ...
    cd /usr/lib/python2.7/site-packages/keystone/identity && \
    patch -f -p0 < /opt/keystone/core.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/common && \
    patch -f -p0 < /opt/keystone/manager.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/auth && \
    patch -f -p0 < /opt/keystone/core_auth.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/server && \
    patch -f -p0 < /opt/keystone/backends.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/server/flask && \
    patch -f -p0 < /opt/keystone/application.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/auth && \
    patch -f -p0 < /opt/keystone/auth_controllers.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/auth/plugins && \
    patch -f -p0 < /opt/keystone/auth_plugins_token.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/common && \
    patch -f -p0 < /opt/keystone/common_controller.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/models && \
    patch -f -p0 < /opt/keystone/token_model.patch && \
    cd /usr/lib/python2.7/site-packages/keystone/token && \
    patch -f -p0 < /opt/keystone/token_provider.patch && \
    find /usr/lib/python2.7/site-packages/keystone -name "*.pyc" -delete && \
    find /usr/lib/python2.7/site-packages/keystone -name "*.pyo" -delete && \
    # Cron task to rotate fernet tokens once a day
    echo "0 1 * * * root /usr/bin/keystone-manage fernet_rotate --keystone-user keystone --keystone-group keystone" >/etc/cron.d/fernetrotate && \
    # Cleaning unused files...
    rpm -e --nodeps redhat-logos || true && yum -y erase libss && \
    yum clean all && rm -rf /var/lib/yum/yumdb && \
    rm -rf /var/lib/yum/history && find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en' ! -name 'es' ! -name 'es_ES' | xargs rm -r && \
    rm -rf ~/fiware-keystone && rm -f /var/log/*log && rm -f /opt/keystone/*.rpm


# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]


EXPOSE 5001 35357

