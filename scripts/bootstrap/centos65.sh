#
# Copyright 2015 Telefonica Investigacion y Desarrollo, S.A.U
#
# This file is part of spassword.
#
# spassword is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# spassword is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Orion Context Broker. If not, see http://www.gnu.org/licenses/.
#
# For those usages not covered by this license please contact with
# iot_support at tid dot es
#
# Author: IoT Platform Team
#

# Setting up EPEL Repo
wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
sudo rpm -ivh epel-release-6-8.noarch.rpm
sudo sed -i "s/#baseurl/baseurl/" /etc/yum.repos.d/epel.repo

sudo yum -y install rpm-build
sudo yum -y install python git python-pip python-devel python-virtualenv gcc ssh

sudo yum install -y https://repos.fedorapeople.org/repos/openstack/EOL/openstack-icehouse/rdo-release-icehouse-4.noarch.rpm
sudo yum install -y openstack-utils openstack-keystone python-keystoneclient
sudo yum install -y wget unzip nc jq 
sudo yum install -y cracklib cracklib-python

sudo yum -y install mysql-server mysql
sudo service mysqld start

sudo mkdir ~/.ssh
sudo echo "Host      pdihub.hi.inet
  Hostname        pdihub.hi.inet
  StrictHostKeyChecking no
  IdentityFile    ~/.ssh/id_rsa_pdihub" > ~/.ssh/config

sudo echo "-----BEGIN DSA PRIVATE KEY-----
MIIBvAIBAAKBgQDod9JbsS3PaK60T6cDVnk4eT04CMRjyoA/CGT05Uh+InpQpB/a
1j+E9kUztZfyNg3B4xozWXu1zUNsE/Hh6KXHff4ZJfbj4owcoW2dzcsSHGkPn61z
GhBZa5PD3PlIcknBsAIKXjUUVL3f+GaWVTQBIm3moAal3qxuemxFz+hr+QIVAKCV
mfVNCs2laMcXHvtXcplqokHrAoGBAIHcci/y0qIog5jMN5RWYpwajak1On55efeX
ZMWuJeQLGN3P4lYdaqmJH3a6a4wJTRq4IUEQMk141iYneXFmdrzpShUWLDTbtMeE
pgsE1wVnjNs5F+AQfhLn+3UJWsPaUYuUN8/5YiS4CmraFSL3qPYOw1J7+OwRLUQG
0b3RMn0JAoGBANmqUtWDqbM0wzzjgXmeN7RyIVt/nvtjVB3hGrbKfXAQYcMp34B/
lbcvcthtKHcPR5+mOljcqJQhYTVhF4IEcJJeDFPb/A+p+yvqJnvm+mQas76ne+aH
f0l0BxiwY8toMnlOjED3aiXx99kJjt3g5dPH9PMbla1Nblh5gp0mIWl9AhRyXGXC
6MTy0yRRjba3BDiwf4G8JQ==
-----END DSA PRIVATE KEY-----" > ~/.ssh/id_rsa_pdihub

sudo chmod 700 ~/.ssh/id_rsa_pdihub


sudo openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:keystone@localhost/keystone

sudo openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ADMIN

sudo openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001

sudo openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true

sudo openstack-config --set /etc/keystone/keystone.conf \
    token provider keystone.token.providers.uuid.Provider

cat <<EOF | mysql -u root
CREATE DATABASE keystone;
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' \
  IDENTIFIED BY 'keystone';
GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' \
  IDENTIFIED BY 'keystone';
EOF

su -s /bin/sh -c "keystone-manage db_sync" keystone

sudo keystone-manage pki_setup --keystone-user keystone --keystone-group keystone
sudo chown -R keystone:keystone /etc/keystone/ssl 
sudo chmod -R o-rwx /etc/keystone/ssl

sudo service openstack-keystone start

sudo chkconfig openstack-keystone on


mkdir updates
cd updates

tag="develop"
user="telefonicaid"

repo_scim="fiware-keystone-scim"
pack_scim="package-keystone-scim.sh"

url_scim="https://github.com/${user}/${repo_scim}/archive/${tag}.tar.gz"

dir=~/updates/fiware-keystone
rm -fR $dir && mkdir -p $dir

curl -s --insecure -L "${url_scim}" | tar zxvf - -C ${dir}

pushd .
cd ${dir}/${repo_scim}-${tag}
source ./${pack_scim}

find . -name "*.rpm" -exec sudo rpm -Uvh {} \;

popd

sudo service openstack-keystone restart

# #############
user="fiware"
repo_spassword="keystone-spassword"
pack_spassword="package-keystone-spassword.sh"
url_spassword="https://pdihub.hi.inet/${user}/${repo_spassword}/archive/${tag}.tar.gz"

cd $dir
git clone git@pdihub.hi.inet:fiware/keystone-spassword.git ${repo_spassword}-${tag}

pushd .
cd ${dir}/${repo_spassword}-${tag}
source ./${pack_spassword}

find . -name "*.rpm" -exec sudo rpm -Uvh {} \;

popd

sudo service openstack-keystone restart


######

export OS_SERVICE_TOKEN=ADMIN
export OS_SERVICE_ENDPOINT=http://localhost:35357/v2.0
readonly KEYSTONE_HOST="localhost:5001"

keystone user-create --name=admin --pass=admin_4passw0rd --email=admin@no.com

keystone role-create --name=admin

keystone tenant-create --name=admin --description="Admin Tenant"

keystone user-role-add --user=admin --tenant=admin --role=admin

keystone role-create --name=service

keystone user-create --name=iotagent --pass=i0ta6ent --email=iotagent@no.com

ADMIN_TOKEN=$(\
    curl http://${KEYSTONE_HOST}/v3/auth/tokens \
         -s \
         -i \
         -H "Content-Type: application/json" \
         -d '
  {
      "auth": {
          "identity": {
              "methods": [
                  "password"
              ],
              "password": {
                  "user": {
                      "domain": {
                          "name": "Default"
                      },
                      "name": "admin",
                      "password": "admin_4passw0rd"
                  }
              }
          },
          "scope": {
              "project": {
                  "domain": {
                      "name": "Default"
                  },
                  "name": "admin"
              }
          }
      }
  }' | grep ^X-Subject-Token: | awk '{print $2}' )

echo "ADMIN_TOKEN: $ADMIN_TOKEN"

ID_ADMIN_DOMAIN=$(\
    curl http://${KEYSTONE_HOST}/v3/domains \
         -s \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
         -H "Content-Type: application/json" \
         -d '
  {
      "domain": {
      "enabled": true,
      "name": "admin_domain"
      }
  }' | jq .domain.id | tr -d '"' )
echo "ID_ADMIN_DOMAIN: $ID_ADMIN_DOMAIN"

ID_CLOUD_SERVICE=$(\
    curl http://${KEYSTONE_HOST}/v3/users \
         -s \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
         -H "Content-Type: application/json" \
         -d '
  {
      "user": {
          "description": "Cloud service",
          "domain_id": "'$ID_ADMIN_DOMAIN'",
          "enabled": true,
          "name": "pep",
          "password": "pep_4passw0rd"
      }
  }' | jq .user.id | tr -d '"' )
echo "ID_CLOUD_SERVICE: $ID_CLOUD_SERVICE"

ID_CLOUD_ADMIN=$(\
    curl http://${KEYSTONE_HOST}/v3/users \
         -s \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
         -H "Content-Type: application/json" \
         -d '
  {
      "user": {
          "description": "Cloud administrator",
          "domain_id": "'$ID_ADMIN_DOMAIN'",
          "enabled": true,
          "name": "cloud_admin",
          "password": "cloud_admin_4passw0rd"
      }
  }' | jq .user.id | tr -d '"' ) 
echo "ID_CLOUD_ADMIN: $ID_CLOUD_ADMIN"

ADMIN_ROLE_ID=$(\
    curl "http://${KEYSTONE_HOST}/v3/roles?name=admin" \
         -s \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
        | jq .roles[0].id | tr -d '"' )
echo "ADMIN_ROLE_ID: $ADMIN_ROLE_ID"


curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_ADMIN}/roles/${ADMIN_ROLE_ID} \
     -s \
     -i \
     -H "X-Auth-Token: $ADMIN_TOKEN" \
     -H "Content-Type: application/json"

SERVICE_ROLE_ID=$(\
    curl "http://${KEYSTONE_HOST}/v3/roles?name=service" \
         -s \
         -H "X-Auth-Token: $ADMIN_TOKEN" \
        | jq .roles[0].id | tr -d '"' )

  curl -X PUT http://${KEYSTONE_HOST}/v3/domains/${ID_ADMIN_DOMAIN}/users/${ID_CLOUD_SERVICE}/roles/${SERVICE_ROLE_ID} \
      -s \
      -i \
      -H "X-Auth-Token: $ADMIN_TOKEN" \
      -H "Content-Type: application/json"

  curl -s -L --insecure https://github.com/openstack/keystone/raw/icehouse-eol/etc/policy.v3cloudsample.json \
  | jq ' .["identity:scim_create_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id" 
     | .["identity:scim_list_roles"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_get_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_update_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_delete_role"]="rule:cloud_admin or rule:admin_and_matching_domain_id"
     | .["identity:scim_get_service_provider_configs"]=""
     | .["identity:get_domain"]=""
     | .admin_and_user_filter="role:admin and \"%\":%(user.id)%"
     | .admin_and_project_filter="role:admin and \"%\":%(scope.project.id)%"
     | .["identity:list_role_assignments"]="rule:admin_on_domain_filter or rule:cloud_service or rule:admin_and_user_filter or rule:admin_and_project_filter"
     | .["identity:list_projects"]="rule:cloud_admin or rule:admin_and_matching_domain_id or rule:cloud_service"
     | .cloud_admin="rule:admin_required and domain_id:'${ID_ADMIN_DOMAIN}'"
     | .cloud_service="rule:service_role and domain_id:'${ID_ADMIN_DOMAIN}'"' \
  | sudo tee /etc/keystone/policy.json 

sudo service openstack-keystone restart
