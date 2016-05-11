FROM centos:6

MAINTAINER IoT team

ENV DB_HOST localhost
ENV KEYSTONE_ADMIN_PASSWORD 4pass1w0rd
ENV KEYSTONE_SCIM_VERSION 0.4.1
ENV KEYSTONE_SPASSWORD_VERSION 0.2.1


RUN \
    # Install dependencies
    yum update -y && yum install -y wget  && \
    wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm  && \
    yum localinstall -y --nogpgcheck epel-release-6-8.noarch.rpm  && \
    # Install MySQL client
    yum -y install mysql  && \
    # Install keystone dependencies
    yum -y install rpm-build && \
    yum -y install python git python-pip python-devel python-virtualenv gcc ssh && \
    yum install -y https://repos.fedorapeople.org/repos/openstack/EOL/openstack-icehouse/rdo-release-icehouse-4.noarch.rpm && \
    # This is a patch to allow the EOL version to work
    sed -i "s/baseurl=.*/baseurl=https:\/\/repos.fedorapeople.org\/repos\/openstack\/EOL\/openstack-icehouse\/epel-6/" /etc/yum.repos.d/rdo-release.repo && \
    # Install keystone dependencies
    yum -y install openstack-utils openstack-keystone python-keystoneclient  && \
    yum -y install curl unzip nc jq  && \
    yum -y install cracklib cracklib-python && \
    # Set keystone configuration
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:keystone@db/keystone && \
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ADMIN  && \
    openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001  && \
    openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true  && \
    openstack-config --set /etc/keystone/keystone.conf \
    token provider keystone.token.providers.uuid.Provider && \
    openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:keystone@$DB_HOST/keystone && \
    # Set keystone SSL configuration
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone  && \
    chown -R keystone:keystone /etc/keystone/ssl && \
    chmod -R o-rwx /etc/keystone/ssl && \
    # Create /opt/keystone
    mkdir -p /opt/keystone

COPY ./keystone-entrypoint.sh /opt/keystone
COPY ./postlaunchconfig.sh /opt/keystone

WORKDIR /opt/keystone

RUN \
    # Keystone postconfig file
    chmod 755 /opt/keystone/postlaunchconfig.sh && \
    chmod 755 /opt/keystone/keystone-entrypoint.sh && \
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
    source ./${pack_scim} && \
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    # Install Keystone-SPASSWORD
    tag=$KEYSTONE_SPASSWORD_VERSION && \
    user="telefonicaid" && \
    repo_spassword="fiware-keystone-spassword" && \
    pack_spassword="package-keystone-spassword.sh" && \
    url_spassword="https://github.com/${user}/${repo_spassword}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_spassword}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_spassword}-${tag} && \
    source ./${pack_spassword} && \
    find . -name "*.rpm" -exec rpm -Uvh {} \;


WORKDIR /opt/keystone

# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]

EXPOSE 5001
