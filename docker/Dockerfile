ARG  IMAGE_TAG=12.4-slim
FROM debian:${IMAGE_TAG}


MAINTAINER IoT team

ENV DB_HOST localhost
ENV KEYSTONE_ADMIN_PASSWORD 4pass1w0rd
ENV KEYSTONE_SCIM_VERSION 1.7.0
#ENV KEYSTONE_SPASSWORD_VERSION 1.17.0
ENV KEYSTONE_SPASSWORD_VERSION python39e

COPY ./*.sh /opt/keystone/
COPY ./*.patch /opt/keystone/
COPY ./*.rpm /opt/keystone/
COPY ./*.json /opt/keystone/
COPY ./*.py /opt/keystone/
COPY ./*.cfg /opt/keystone/
COPY ./keystone-all /opt/keystone/

WORKDIR /opt/keystone

RUN \
    # Install security updates
    apt-get -y update && \
    apt-get -y upgrade && \
    # Install MySQL client
    apt-get -y install \
      mariadb-client \
      git \
      sed \
      tar \
      procps \
      python3-dev \
      python3-pip \
      netcat-traditional \
      cron \
      rpm \
      findutils && \
    # Install keystone dependencies
    apt-get -y install \
       crudini \
       keystone \
       python3-keystoneclient \
    python3-openstackclient && \
    # Install keystone dependencies
    apt-get -y install \
       apache2 \
       libapache2-mod-wsgi-py3 && \
    sed -i 's/#ServerName www.example.com:80/ServerName 127.0.0.1 /g' /etc/apache2/apache2.conf && \
    sed -i 's/5000/5001/g' /usr/share/keystone/wsgi-keystone.conf && \
    ln -s /usr/share/keystone/wsgi-keystone.conf /etc/apache2/conf-enabled/ && \
    systemctl enable apache2.service && \
    cp /opt/keystone/keystone-all /usr/bin && \
    chmod 755 /usr/bin/keystone-all && \
    cp /opt/keystone/openstack-config.sh /usr/bin/openstack-config && \
    chmod 755 /usr/bin/openstack-config && \
    apt-get -y install unzip jq python3-redis && \
    echo "INFO: install cracklib...\n" && \
    apt-get -y install python3-cracklib && \
    #pip3 install cracklib && \
    # Set keystone configuration
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001  && \
    openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true  && \
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql+pymysql://keystone:keystone@$DB_HOST/keystone && \
    # Set log configuration
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT default_log_levels amqp=WARN,amqplib=WARN,boto=WARN,qpid=WARN,sqlalchemy=WARN,suds=INFO,oslo.messaging=INFO,oslo_messaging=INFO,iso8601=WARN,requests.packages.urllib3.connectionpool=WARN,urllib3.connectionpool=WARN,websocket=WARN,requests.packages.urllib3.util.retry=WARN,urllib3.util.retry=WARN,keystonemiddleware=WARN,routes.middleware=WARN,stevedore=ERROR,taskflow=WARN,keystoneauth=WARN,oslo.cache=INFO,oslo.policy=ERROR,oslo_policy=ERROR,dogpile.core.dogpile=INFO,keystone.server.flask.application=ERROR && \
    mkdir -p /etc/keystone/policy.d && \
    chown keystone.keystone /etc/keystone/policy.d && \
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
    mkdir -p /usr/lib/python3.9/site-packages/keystone/contrib && \
    touch /usr/lib/python3.9/site-packages/keystone/contrib/__init__.py && \
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
    source ./${pack_scim} --with-python39 --with-version $KEYSTONE_SCIM_VERSION --with-release 0 && \
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
    source ./${pack_spassword} --with-python39 --with-version $KEYSTONE_SPASSWORD_VERSION --with-release 0 && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # LDAP pre-support
    apt-get -y install openldap-clients && \
    mkdir -p /etc/ldap && \
    ln -s /etc/openldap/ldap.conf /etc/ldap/ldap.conf && \
    mkdir -p /etc/keystone/domains && \
    chown keystone.keystone /etc/keystone/domains && \
    openstack-config --set /etc/keystone/keystone.conf \
    identity domain_specific_drivers_enabled true && \
    openstack-config --set /etc/keystone/keystone.conf \
    identity domain_config_dir /etc/keystone/domains && \
    # Federation by SAML2 pre-support
    apt-get install -y xmlsec1 && \
    # Patching ...
    ln -s /usr/lib/python3.9/site-packages/keystone/contrib/scim/scim.py  /usr/lib/python3.9/site-packages/keystone/api && \
    ln -s /usr/lib/python3.9/site-packages/keystone/contrib/spassword/spassword.py  /usr/lib/python3.9/site-packages/keystone/api && \
    rm -f /usr/lib/python3.9/site-packages/keystone/contrib/spassword/controllers.* && \
    rm -f /usr/lib/python3.9/site-packages/keystone/contrib/spassword/routers.* && \
    rm -f /usr/lib/python3.9/site-packages/keystone/contrib/scim/controllers.* && \
    rm -f /usr/lib/python3.9/site-packages/keystone/contrib/scim/routers.* && \
    cd /usr/lib/python3.9/site-packages/keystone/identity && \
    patch -f -p0 < /opt/keystone/core.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/common && \
    patch -f -p0 < /opt/keystone/manager.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/auth && \
    patch -f -p0 < /opt/keystone/core_auth.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/server && \
    patch -f -p0 < /opt/keystone/backends.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/auth/plugins && \
    patch -f -p0 < /opt/keystone/auth_plugins_token.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/common && \
    patch -f -p0 < /opt/keystone/common_render_token.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/models && \
    patch -f -p0 < /opt/keystone/token_model.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/token && \
    patch -f -p0 < /opt/keystone/token_provider.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/api && \
    patch -f -p0 < /opt/keystone/apis.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/api && \
    patch -f -p0 < /opt/keystone/api_role_assignments.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/api && \
    patch -f -p0 < /opt/keystone/projects.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/api/_shared && \
    patch -f -p0 < /opt/keystone/api_auth.patch && \
    cd /usr/lib/python3.9/site-packages/keystone/common/sql/legacy_migrations/expand_repo/versions && \
    patch -f -p0 < /opt/keystone/expand_initial_migration.patch && \
    find /usr/lib/python3.9/site-packages/keystone -name "*.pyc" -delete && \
    find /usr/lib/python3.9/site-packages/keystone -name "*.pyo" -delete && \
    sed -ri \
              -e 's!^(\s*CustomLog)\s+\S+!\1 /proc/1/fd/1!g' \
              -e 's!^(\s*ErrorLog)\s+\S+!\1 /proc/1/fd/2!g' \
              /etc/apache2/conf-enabled/wsgi-keystone.conf && \
    rm /etc/keystone/logging.conf && \
    # Cleaning unused files...
    apt-get remove -y python3-devel && \
    apt-get -y autoremove --purge && \
    find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en' ! -name 'es' ! -name 'es_ES' | xargs rm -r && \
    rm -rf ~/fiware-keystone && rm -f /var/log/*log && rm -f /opt/keystone/*.rpm


# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]

EXPOSE 5001 35357

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
            CMD curl --fail -X GET http://localhost:5001/v3 || exit 1
