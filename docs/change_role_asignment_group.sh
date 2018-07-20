DELETE http://orchestrator_host:8084/v1.0/service/<serviceId>/group_role_assignments
{
  "SERVICE_ADMIN_USER": "test_admin_service",
  "SERVICE_ADMIN_PASSWORD": "passwd",
  "SERVICE_ADMIN_TOKEN": "token",
  "ROLE_NAME": "SubServiceCustomer",
  "ROLE_ID": "sadfasdfasd5674567fas",
  "GROUP_NAME": "group_nameX",
  "GROUP_ID": "asd54634574567fasdf",
}

PUT  http://orchestrator_host:8084/v1.0/service/<serviceId>/group_role_assignments
{
  "SUBSERVICE_NAME":"test_subservice",
  "SUBSERVICE_ID":"234234234234sdfgdfghdfgh",
  "SERVICE_ADMIN_USER": "test_admin_service",
  "SERVICE_ADMIN_PASSWORD": "passwd",
  "SERVICE_ADMIN_TOKEN": "token",
  "ROLE_NAME": "ServiceCustomer",
  "ROLE_ID": "sadfasdfasd5674567fas",
  "GROUP_NAME": "group_nameX",
  "GROUP_ID": "asd54634574567fasdf",
  "INHERIT": false
}
