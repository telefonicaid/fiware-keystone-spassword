FROM debian:bookworm-slim

MAINTAINER IoT team

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DB_HOST=localhost \
    KEYSTONE_SCIM_VERSION=1.8.0 \
    KEYSTONE_SPASSWORD_VERSION=1.24.0 \
    PATH=/opt/keystone-venv/bin:$PATH

ARG KEYSTONE_REVISION=35308cbe6102ecb8757fe0a53fbe9219f06c3903
ARG REQUIREMENTS_REVISION=ae79a47881a3595ee80a825e4dadf3217dcac024

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y upgrade && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates curl git tar patch findutils procps cron \
        mariadb-client postgresql-client apache2 libapache2-mod-wsgi-py3 \
        python3 python3-venv python3-dev gcc libc6-dev libcrack2-dev \
        cracklib-runtime ldap-utils libldap-common libldap2-dev libsasl2-dev xmlsec1 \
        crudini netcat-openbsd jq unzip && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/keystone-venv && \
    curl -fsSL "https://opendev.org/openstack/requirements/raw/commit/${REQUIREMENTS_REVISION}/upper-constraints.txt" \
        -o /tmp/upper-constraints.txt && \
    git clone https://opendev.org/openstack/keystone.git /tmp/keystone && \
    git -C /tmp/keystone checkout --detach "${KEYSTONE_REVISION}" && \
    pip install --no-cache-dir -c /tmp/upper-constraints.txt \
        '/tmp/keystone[ldap]' 'python-keystoneclient==5.7.0' \
        python-openstackclient PyMySQL psycopg2-binary redis cracklib && \
    pip check

COPY ./*.sh ./*.patch ./*.json ./keystone-all /opt/keystone/
COPY ./keystone-wsgi.conf /etc/apache2/conf-available/keystone-wsgi.conf
COPY ./keystone.wsgi /opt/keystone/keystone.wsgi

WORKDIR /opt/keystone

RUN groupadd --system keystone && \
    useradd --system --gid keystone --home-dir /var/lib/keystone \
        --shell /sbin/nologin keystone && \
    mkdir -p /etc/keystone/domains /etc/keystone/policy.d \
        /etc/keystone/fernet-keys /var/lib/keystone /var/log/keystone && \
    chown -R keystone:keystone /etc/keystone/domains /etc/keystone/policy.d \
        /etc/keystone/fernet-keys /var/lib/keystone /var/log/keystone && \
    chmod 750 /etc/keystone/fernet-keys && \
    cp /tmp/keystone/etc/sso_callback_template.html /etc/keystone/ && \
    touch /etc/keystone/keystone.conf && \
    chown root:keystone /etc/keystone/keystone.conf && \
    chmod 640 /etc/keystone/keystone.conf && \
    ln -s /opt/keystone-venv/bin/keystone-manage /usr/bin/keystone-manage && \
    cp /opt/keystone/openstack-config.sh /usr/bin/openstack-config && \
    cp /opt/keystone/keystone-all /usr/bin/keystone-all && \
    chmod 755 /usr/bin/openstack-config /usr/bin/keystone-all \
        /opt/keystone/postlaunchconfig.sh /opt/keystone/postlaunchconfig_update.sh \
        /opt/keystone/keystone-entrypoint.sh && \
    openstack-config --set /etc/keystone/keystone.conf DEFAULT public_port 5001 && \
    openstack-config --set /etc/keystone/keystone.conf os_inherit enabled true && \
    openstack-config --set /etc/keystone/keystone.conf token provider fernet && \
    openstack-config --set /etc/keystone/keystone.conf fernet_tokens max_active_keys 6 && \
    openstack-config --set /etc/keystone/keystone.conf identity domain_specific_drivers_enabled true && \
    openstack-config --set /etc/keystone/keystone.conf identity domain_config_dir /etc/keystone/domains && \
    openstack-config --set /etc/keystone/keystone.conf identity driver keystone_spassword.contrib.spassword.backends.sql.Identity && \
    openstack-config --set /etc/keystone/keystone.conf auth password keystone_spassword.contrib.spassword.SPassword && \
    openstack-config --set /etc/keystone/keystone.conf spassword enabled true && \
    openstack-config --set /etc/keystone/keystone.conf spassword pwd_max_tries 5 && \
    openstack-config --set /etc/keystone/keystone.conf spassword pwd_user_blacklist '' && \
    openstack-config --set /etc/keystone/keystone.conf spassword smtp_user smtpuser@yourdomain.com && \
    openstack-config --set /etc/keystone/keystone.conf spassword smtp_password yourpassword && \
    openstack-config --set /etc/keystone/keystone.conf spassword smtp_from smtpuser && \
    keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone && \
    mkdir -p /tmp/scim /tmp/spassword && \
    curl -fsSL "https://github.com/telefonicaid/fiware-keystone-scim/archive/refs/tags/${KEYSTONE_SCIM_VERSION}.tar.gz" | \
        tar -xz --strip-components=1 -C /tmp/scim && \
    curl -fsSL "https://github.com/telefonicaid/fiware-keystone-spassword/archive/refs/tags/${KEYSTONE_SPASSWORD_VERSION}.tar.gz" | \
        tar -xz --strip-components=1 -C /tmp/spassword && \
    site=$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))') && \
    cp -a /tmp/scim/keystone_scim "$site/" && \
    cp -a /tmp/spassword/keystone_spassword "$site/" && \
    mkdir -p "$site/keystone/contrib" && \
    touch "$site/keystone/contrib/__init__.py" && \
    ln -s "$site/keystone_scim/contrib/scim" "$site/keystone/contrib/scim" && \
    ln -s "$site/keystone_spassword/contrib/spassword" "$site/keystone/contrib/spassword" && \
    ln -s "$site/keystone/contrib/scim/scim.py" "$site/keystone/api/scim.py" && \
    ln -s "$site/keystone/contrib/spassword/spassword.py" "$site/keystone/api/spassword.py" && \
    ln -s "$site/keystone_spassword/contrib/spassword/migrate_repo/versions/1_spassword.py" \
        "$site/keystone/common/sql/migrations/versions/1_spassword.py" && \
    rm -f "$site/keystone/contrib/"{spassword,scim}/{controllers,routers}.py && \
    cd "$site/keystone/identity" && patch -f --fuzz=0 -p0 < /opt/keystone/core.patch && \
    cd "$site/keystone/common" && patch -f --fuzz=0 -p0 < /opt/keystone/manager.patch && \
    cd "$site/keystone/auth" && patch -f --fuzz=0 -p0 < /opt/keystone/core_auth.patch && \
    cd "$site/keystone/server" && patch -f --fuzz=0 -p0 < /opt/keystone/backends.patch && \
    cd "$site/keystone/auth/plugins" && patch -f --fuzz=0 -p0 < /opt/keystone/auth_plugins_token.patch && \
    cd "$site/keystone/common" && patch -f --fuzz=0 -p0 < /opt/keystone/common_render_token.patch && \
    cd "$site/keystone/models" && patch -f --fuzz=0 -p0 < /opt/keystone/token_model.patch && \
    cd "$site/keystone/token" && patch -f --fuzz=0 -p0 < /opt/keystone/token_provider.patch && \
    cd "$site/keystone/contrib/spassword" && patch -f --fuzz=0 -p0 < /opt/keystone/spassword_api.patch && \
    cd "$site/keystone/server/flask" && patch -f --fuzz=0 -p0 < /opt/keystone/apis.patch && \
    cd "$site/keystone/api" && patch -f --fuzz=0 -p0 < /opt/keystone/api_role_assignments.patch && \
    patch -f --fuzz=0 -p0 < /opt/keystone/projects.patch && \
    cd "$site/keystone/api/_shared" && patch -f --fuzz=0 -p0 < /opt/keystone/api_auth.patch && \
    find "$site/keystone" "$site/keystone_spassword" "$site/keystone_scim" -name '*.pyc' -delete && \
    a2dissite 000-default && \
    a2enconf keystone-wsgi && \
    sed -i '/^Listen 80$/d' /etc/apache2/ports.conf && \
    echo 'ServerName 127.0.0.1' >> /etc/apache2/apache2.conf && \
    rm -rf /tmp/keystone /tmp/scim /tmp/spassword /tmp/upper-constraints.txt

ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]

EXPOSE 5001 35357

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
            CMD curl --fail -X GET http://localhost:5001/v3 || exit 1
