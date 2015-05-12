#
# Copyright 2015 Telefonica Investigacion y Desarrollo, S.A.U
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import functools

from keystone.common import json_home
from keystone.common import wsgi
from keystone_spassword.contrib.spassword import controllers


class PasswordExtension(wsgi.ExtensionRouter):

    def add_routes(self, mapper):

        scim_user_controller = controllers.SPasswordScimUserV3Controller()
        user_controller = controllers.SPasswordUserV3Controller()

        # SCIM User Operations
        mapper.connect(
            '/OS-SCIM/Users/{user_id}',
            controller=scim_user_controller,
            action='patch_user',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/OS-SCIM/Users/{user_id}',
            controller=scim_user_controller,
            action='put_user',
            conditions=dict(method=['PUT']))

        # User Operations
        mapper.connect(
            '/users',
            controller=user_controller,
            action='create_user',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/users',
            controller=user_controller,
            action='update_user',
            conditions=dict(method=['PUT']))

        mapper.connect(
            '/users/{user_id}/password',
            controller=user_controller,
            action='change_password',
            conditions=dict(method=['POST']))

        # New User operations: recover password
        mapper.connect(
            '/users/{user_id}/recover_password',
            controller=user_controller,
            action='recover_password',
            conditions=dict(method=['GET']))

        # Create user using OS-SCIM API
        mapper.connect(
            '/OS-SCIM/Users',
            controller=scim_user_controller,
            action='create_user',
            conditions=dict(method=['POST']))
