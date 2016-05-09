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
    yum -y install wget unzip nc jq  && \
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
    find . -name "*.rpm" -exec rpm -Uvh {} \; && \
    mkdir -p /opt/keystone

COPY keystone-entrypoint.sh /opt/keystone

# The following sections build a script that will be executed on launch via ENTRYPOINT
#https://allthingsopen.com/2014/07/09/docker-all-the-things-openstack-keystone-and-ceilometer-automated-builds-on-docker-hub/

## Start Keystone
RUN echo "#!/bin/bash" > /opt/keystone/postlaunchconfig.sh && \
    echo " \
DB_HOST_ARG=\${1}                                                         \
DB_HOST_VALUE=\${2}                                                       \
if [ \"\$DB_HOST_ARG\" == \"-dbhost\" ]; then                             \
    openstack-config --set /etc/keystone/keystone.conf                    \
    database connection mysql://keystone:keystone@$DB_HOST_VALUE/keystone \
fi                                                                        \
                                                                          \
/usr/bin/keystone-manage db_sync keystone                                 \
/usr/bin/keystone-manage db_sync --extension spassword                    \
/usr/bin/keystone-all & " >> /opt/keystone/postlaunchconfig.sh && \

# Create Services
# I'm not sure if exporting works, so I just specify these environment
# variables on each command, but it might be cleaner to test this

    echo " \
export OS_SERVICE_TOKEN=ADMIN                                                 \
export OS_SERVICE_ENDPOINT=http://localhost:35357/v2.0                        \
readonly KEYSTONE_HOST=\"localhost:5001\"                                     \
keystone user-create --name=admin --pass=$KEYSTONE_ADMIN_PASSWORD --email=admin@no.com \
keystone role-create --name=admin                                             \
keystone tenant-create --name=admin --description=\"Admin Tenant\"            \
keystone user-role-add --user=admin --tenant=admin --role=admin               \
keystone role-create --name=service                                           \
keystone user-create --name=iotagent --pass=$KEYSTONE_ADMIN_PASSWORD --email=iotagent@no.com" >> /opt/keystone/postlaunchconfig.sh && \

    echo "ADMIN_TOKEN=\$(\
curl http://\${KEYSTONE_HOST}/v3/auth/tokens         \
         -s                                          \
         -i                                          \
         -H \"Content-Type: application/json\"       \
         -d '                                        \
     {                                               \
      \"auth\": {                                    \
          \"identity\": {                            \
              \"methods\": [                         \
                  \"password\"                       \
              ],                                     \
              \"password\": {                        \
                  \"user\": {                        \
                      \"domain\": {                  \
                          \"name\": \"Default\       \
                      },                             \
                      \"name\": \"admin\",           \
                      \"password\": \"$KEYSTONE_ADMIN_PASSWORD\"   \
                  }                                  \
              }                                      \
          },                                         \
          \"scope\": {                               \
              \"project\": {                         \
                  \"domain\": {                      \
                      \"name\": \"Default\"          \
                  },                                 \
                  \"name\": \"admin\"                \
              }                                      \
          }                                          \
      }                                              \
    }' | grep ^X-Subject-Token: | awk '{print \$2}' )" >> /opt/keystone/postlaunchconfig.sh && \
    echo "echo \"ADMIN_TOKEN: \$ADMIN_TOKEN\"" >> /opt/keystone/postlaunchconfig.sh && \

    echo "ID_ADMIN_DOMAIN=\$(                       \
curl http://\${KEYSTONE_HOST}/v3/domains            \
         -s                                         \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\"         \
         -H \"Content-Type: application/json\"      \
         -d '                                       \
  {                                                 \
      \"domain\": {                                 \
      \"enabled\": true,                            \
      \"name\": \"admin_domain\"                    \
      }                                             \
  }' | jq .domain.id | tr -d '\"' )" >> /opt/keystone/postlaunchconfig.sh && \
    echo "echo \"ID_ADMIN_DOMAIN: \$ID_ADMIN_DOMAIN\"" >> /opt/keystone/postlaunchconfig.sh && \

    echo "ID_CLOUD_SERVICE=\$(                      \
curl http://\${KEYSTONE_HOST}/v3/users              \
         -s                                         \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\"         \
         -H \"Content-Type: application/json\"      \
         -d '                                       \
  {                                                 \
      \"user\": {                                   \
          \"description\": \"Cloud service\",       \
          \"domain_id\": \"'\$ID_ADMIN_DOMAIN'\",   \
          \"enabled\": true,                        \
          \"name\": \"pep\",                        \
          \"password\": \"$KEYSTONE_ADMIN_PASSWORD\"\
      }                                             \
  }' | jq .user.id | tr -d '\"' )" >> /opt/keystone/postlaunchconfig.sh && \
    echo "echo \"ID_CLOUD_SERVICE: \$ID_CLOUD_SERVICE\"" >> /opt/keystone/postlaunchconfig.sh && \

    echo "ID_CLOUD_ADMIN=\$(                        \
curl http://\${KEYSTONE_HOST}/v3/users              \
         -s                                         \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\"         \
         -H \"Content-Type: application/json\"      \
         -d '                                       \
  {                                                 \
      \"user\": {                                   \
          \"description\": \"Cloud administrator\", \
          \"domain_id\": \"'\$ID_ADMIN_DOMAIN'\",   \
          \"enabled\": true,                        \
          \"name\": \"cloud_admin\",                \
          \"password\": \"$KEYSTONE_ADMIN_PASSWORD\"\
      }                                             \
  }' | jq .user.id | tr -d '\"' )" >> /opt/keystone/postlaunchconfig.sh && \
    echo "echo \"ID_CLOUD_ADMIN: \$ID_CLOUD_ADMIN\"" >> /opt/keystone/postlaunchconfig.sh && \

    echo "ADMIN_ROLE_ID=\$(\
curl \"http://\${KEYSTONE_HOST}/v3/roles?name=admin\"     \
         -s                                               \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\"               \
        | jq .roles[0].id | tr -d '\"' )" >> /opt/keystone/postlaunchconfig.sh && \
    echo "echo \"ADMIN_ROLE_ID: \$ADMIN_ROLE_ID\" " >> /opt/keystone/postlaunchconfig.sh && \

    echo "curl -X PUT http://\${KEYSTONE_HOST}/v3/domains/\${ID_ADMIN_DOMAIN}/users/\${ID_CLOUD_ADMIN}/roles/\${ADMIN_ROLE_ID} \
     -s                                 \
     -i                                 \
     -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
     -H \"Content-Type: application/json\" ">> /opt/keystone/postlaunchconfig.sh && \

    echo "SERVICE_ROLE_ID=\$(\
curl \"http://\${KEYSTONE_HOST}/v3/roles?name=service\" \
         -s                                             \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\"             \
        | jq .roles[0].id | tr -d '\"' ) ">> /opt/keystone/postlaunchconfig.sh && \

    echo "curl -X PUT http://\${KEYSTONE_HOST}/v3/domains/\${ID_ADMIN_DOMAIN}/users/\${ID_CLOUD_SERVICE}/roles/\${SERVICE_ROLE_ID} \
      -s                                 \
      -i                                 \
      -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
      -H \"Content-Type: application/json\" ">> /opt/keystone/postlaunchconfig.sh && \

   echo "curl -s -L --insecure https://github.com/openstack/keystone/raw/icehouse-eol/etc/policy.v3cloudsample.json \
  | jq ' .[\"identity:scim_create_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"  \
     | .[\"identity:scim_list_roles\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"     \
     | .[\"identity:scim_get_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"       \
     | .[\"identity:scim_update_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"    \
     | .[\"identity:scim_delete_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"    \
     | .[\"identity:scim_get_service_provider_configs\"]=\"\"                                        \
     | .[\"identity:get_domain\"]=\"\"                                                               \
     | .admin_and_user_filter=\"role:admin and \\"%\\":%(user.id)%\"                                 \
     | .admin_and_project_filter=\"role:admin and \\"%\\":%(scope.project.id)%\"                     \
     | .[\"identity:list_role_assignments\"]=\"rule:admin_on_domain_filter or rule:cloud_service or rule:admin_and_user_filter or rule:admin_and_project_filter\"                                                                   \
     | .[\"identity:list_projects\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id or rule:cloud_service\" \
     | .cloud_admin=\"rule:admin_required and domain_id:'\${ID_ADMIN_DOMAIN}'\"                      \
     | .cloud_service=\"rule:service_role and domain_id:'\${ID_ADMIN_DOMAIN}'\"'                     \
  | tee /etc/keystone/policy.json  ">> /opt/keystone/postlaunchconfig.sh && \

  chmod 755 /opt/keystone/postlaunchconfig.sh

WORKDIR /opt/keystone

# Define the entry point
ENTRYPOINT ["/opt/keystone/keystone-entrypoint.sh"]

EXPOSE 5001
