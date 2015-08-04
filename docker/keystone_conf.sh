export OS_SERVICE_TOKEN=ADMIN
export OS_SERVICE_ENDPOINT=http://localhost:35357/v2.0
readonly KEYSTONE_HOST="localhost:5001"

keystone user-create --name=admin --pass=4pass1w0rd --email=admin@no.com

keystone role-create --name=admin

keystone tenant-create --name=admin --description="Admin Tenant"

keystone user-role-add --user=admin --tenant=admin --role=admin

keystone role-create --name=service

keystone user-create --name=iotagent --pass=4pass1w0rd --email=iotagent@no.com

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
                      "password": "4pass1w0rd"
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
          "password": "4pass1w0rd"
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
          "password": "4pass1w0rd"
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
