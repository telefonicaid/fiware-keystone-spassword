FROM centos:6

MAINTAINER IoT team

ENV DB_HOST localhost


RUN \
    # Install dependencies
    yum update -y && yum install -y wget  && \
    wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm  && \
    yum localinstall -y --nogpgcheck epel-release-6-8.noarch.rpm  && \
    # Install MySQL (client at least?)
    yum -y install mysql  && \

    # Install keystone dependencies
    yum -y install rpm-build && \
    yum -y install python git python-pip python-devel python-virtualenv gcc ssh && \
    yum install -y https://repos.fedorapeople.org/repos/openstack/EOL/openstack-icehouse/rdo-release-icehouse-4.noarch.rpm

# This is a patch to allow the EOL version to work
RUN sed -i "s/baseurl=.*/baseurl=https:\/\/repos.fedorapeople.org\/repos\/openstack\/EOL\/openstack-icehouse\/epel-6/" /etc/yum.repos.d/rdo-release.repo

RUN \
    # Install keystone dependencies
    yum -y install openstack-utils openstack-keystone python-keystoneclient  && \
    yum -y install wget unzip nc jq  && \
    yum -y install cracklib cracklib-python


RUN \
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
    database connection mysql://keystone:keystone@$DB_HOST/keystone

RUN \
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone  && \
    chown -R keystone:keystone /etc/keystone/ssl && \
    chmod -R o-rwx /etc/keystone/ssl

RUN \
    # Install Keystone-SCIM
    tag="develop" && \
    user="telefonicaid" && \
    repo_scim="fiware-keystone-scim" && \
    pack_scim="package-keystone-scim.sh" && \
    url_scim="https://github.com/${user}/${repo_scim}/archive/${tag}.tar.gz" && \
    dir=~/fiware-keystone && \
    rm -fR $dir && mkdir -p $dir && \
    curl -s --insecure -L "${url_scim}" | tar zxvf - -C ${dir} && \
    cd ${dir}/${repo_scim}-${tag} && \
    source ./${pack_scim} && \
    find . -name "*.rpm" -exec rpm -Uvh {} \;


RUN \
    # Install Keystone-SPASSWORD
    tag="develop" && \
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


# The following sections build a script that will be executed on launch via ENTRYPOINT
#https://allthingsopen.com/2014/07/09/docker-all-the-things-openstack-keystone-and-ceilometer-automated-builds-on-docker-hub/

## Start Keystone
RUN echo "#!/bin/bash" > /root/postlaunchconfig.sh
RUN echo "/usr/bin/keystone-manage db_sync keystone" >> /root/postlaunchconfig.sh
RUN echo "/usr/bin/keystone-manage db_sync --extension spassword" >> /root/postlaunchconfig.sh
RUN echo "/usr/bin/keystone-all &" >> /root/postlaunchconfig.sh

# Create Services
#I'm not sure if exporting works, so I just specify these environment variables on each command, but it might be cleaner to test this

RUN echo 'export OS_SERVICE_TOKEN=ADMIN' >> /root/postlaunchconfig.sh
RUN echo 'export OS_SERVICE_ENDPOINT=http://localhost:35357/v2.0 ' >> /root/postlaunchconfig.sh
RUN echo 'readonly KEYSTONE_HOST="localhost:5001" ' >> /root/postlaunchconfig.sh
RUN echo 'keystone user-create --name=admin --pass=4pass1w0rd --email=admin@no.com ' >> /root/postlaunchconfig.sh
RUN echo 'keystone role-create --name=admin ' >> /root/postlaunchconfig.sh
RUN echo 'keystone tenant-create --name=admin --description="Admin Tenant" ' >> /root/postlaunchconfig.sh
RUN echo 'keystone user-role-add --user=admin --tenant=admin --role=admin' >> /root/postlaunchconfig.sh
RUN echo 'keystone role-create --name=service ' >> /root/postlaunchconfig.sh
RUN echo 'keystone user-create --name=iotagent --pass=4pass1w0rd --email=iotagent@no.com' >> /root/postlaunchconfig.sh

RUN echo "ADMIN_TOKEN=\$(\
    curl http://\${KEYSTONE_HOST}/v3/auth/tokens \
         -s \
         -i \
         -H \"Content-Type: application/json\" \
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
                      \"password\": \"4pass1w0rd\"   \
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
    }' | grep ^X-Subject-Token: | awk '{print \$2}' )" >> /root/postlaunchconfig.sh

RUN echo "echo \"ADMIN_TOKEN: \$ADMIN_TOKEN\"" >> /root/postlaunchconfig.sh

RUN echo "ID_ADMIN_DOMAIN=\$(\
    curl http://\${KEYSTONE_HOST}/v3/domains \
         -s \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
         -H \"Content-Type: application/json\" \
         -d '                                       \
  {                                                 \
      \"domain\": {                                 \
      \"enabled\": true,                            \
      \"name\": \"admin_domain\"                    \
      }                                             \
  }' | jq .domain.id | tr -d '\"' )" >> /root/postlaunchconfig.sh
RUN echo "echo \"ID_ADMIN_DOMAIN: \$ID_ADMIN_DOMAIN\"" >> /root/postlaunchconfig.sh

RUN echo "ID_CLOUD_SERVICE=\$(\
    curl http://\${KEYSTONE_HOST}/v3/users \
         -s \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
         -H \"Content-Type: application/json\" \
         -d '                                       \
  {                                                 \
      \"user\": {                                   \
          \"description\": \"Cloud service\",       \
          \"domain_id\": \"'\$ID_ADMIN_DOMAIN'\",    \
          \"enabled\": true,                        \
          \"name\": \"pep\",                        \
          \"password\": \"4pass1w0rd\"              \
      }                                             \
  }' | jq .user.id | tr -d '\"' )" >> /root/postlaunchconfig.sh
RUN echo "echo \"ID_CLOUD_SERVICE: \$ID_CLOUD_SERVICE\"" >> /root/postlaunchconfig.sh

RUN echo "ID_CLOUD_ADMIN=\$(\
    curl http://\${KEYSTONE_HOST}/v3/users \
         -s \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
         -H \"Content-Type: application/json\" \
         -d '                                       \
  {                                                 \
      \"user\": {                                   \
          \"description\": \"Cloud administrator\", \
          \"domain_id\": \"'\$ID_ADMIN_DOMAIN'\",   \
          \"enabled\": true,                        \
          \"name\": \"cloud_admin\",                \
          \"password\": \"4pass1w0rd\"              \
      }                                             \
  }' | jq .user.id | tr -d '\"' )" >> /root/postlaunchconfig.sh
RUN echo "echo \"ID_CLOUD_ADMIN: \$ID_CLOUD_ADMIN\"" >> /root/postlaunchconfig.sh

RUN echo "ADMIN_ROLE_ID=\$(\
    curl \"http://\${KEYSTONE_HOST}/v3/roles?name=admin\" \
         -s \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
        | jq .roles[0].id | tr -d '\"' )" >> /root/postlaunchconfig.sh
RUN echo "echo \"ADMIN_ROLE_ID: \$ADMIN_ROLE_ID\" " >> /root/postlaunchconfig.sh


RUN echo "curl -X PUT http://\${KEYSTONE_HOST}/v3/domains/\${ID_ADMIN_DOMAIN}/users/\${ID_CLOUD_ADMIN}/roles/\${ADMIN_ROLE_ID} \
     -s \
     -i \
     -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
     -H \"Content-Type: application/json\" ">> /root/postlaunchconfig.sh

RUN echo "SERVICE_ROLE_ID=\$(\
    curl \"http://\${KEYSTONE_HOST}/v3/roles?name=service\" \
         -s \
         -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
        | jq .roles[0].id | tr -d '\"' ) ">> /root/postlaunchconfig.sh

RUN echo "curl -X PUT http://\${KEYSTONE_HOST}/v3/domains/\${ID_ADMIN_DOMAIN}/users/\${ID_CLOUD_SERVICE}/roles/\${SERVICE_ROLE_ID} \
      -s \
      -i \
      -H \"X-Auth-Token: \$ADMIN_TOKEN\" \
      -H \"Content-Type: application/json\" ">> /root/postlaunchconfig.sh

RUN echo "curl -s -L --insecure https://github.com/openstack/keystone/raw/icehouse-eol/etc/policy.v3cloudsample.json \
  | jq ' .[\"identity:scim_create_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"  \
     | .[\"identity:scim_list_roles\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"     \
     | .[\"identity:scim_get_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"       \
     | .[\"identity:scim_update_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"    \
     | .[\"identity:scim_delete_role\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id\"    \
     | .[\"identity:scim_get_service_provider_configs\"]=\"\"                                        \
     | .[\"identity:get_domain\"]=\"\"                                                               \
     | .admin_and_user_filter=\"role:admin and \\"%\\":%(user.id)%\"                                 \
     | .admin_and_project_filter=\"role:admin and \\"%\\":%(scope.project.id)%\"                     \
     | .[\"identity:list_role_assignments\"]=\"rule:admin_on_domain_filter or rule:cloud_service or rule:admin_and_user_filter or rule:admin_and_project_filter\" \
     | .[\"identity:list_projects\"]=\"rule:cloud_admin or rule:admin_and_matching_domain_id or rule:cloud_service\" \
     | .cloud_admin=\"rule:admin_required and domain_id:'\${ID_ADMIN_DOMAIN}'\"                   \
     | .cloud_service=\"rule:service_role and domain_id:'\${ID_ADMIN_DOMAIN}'\"' \
  | tee /etc/keystone/policy.json  ">> /root/postlaunchconfig.sh

RUN chmod 755 /root/postlaunchconfig.sh
#RUN cat /root/postlaunchconfig.sh

# RUN chkconfig openstack-keystone on
# CMD ["keystone-all"]

EXPOSE 5000 35357
