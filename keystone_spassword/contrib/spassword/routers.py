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

from keystone.common import wsgi
from keystone_spassword.contrib.spassword import controllers


class SPasswordExtension(wsgi.ExtensionRouter):

    # For SCIM API Version 2.0 PATH_PREFIX will be '/OS-SCIM/v1'
    PATH_PREFIX = '/OS-SCIM'

    def add_routes(self, mapper):

        scim_user_controller = controllers.SPasswordScimUserV3Controller()
        user_controller = controllers.SPasswordUserV3Controller()
        spassword_controller = controllers.SPasswordV3Controller()

        # SCIM User Operations
        mapper.connect(
            self.PATH_PREFIX + '/Users/{user_id}',
            controller=scim_user_controller,
            action='patch_user',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            self.PATH_PREFIX + '/Users/{user_id}',
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
            '/users',
            controller=user_controller,
            action='delete_user',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/users/{user_id}/password',
            controller=user_controller,
            action='change_password',
            conditions=dict(method=['POST']))

        # Create user using OS-SCIM API
        mapper.connect(
            self.PATH_PREFIX + '/Users',
            controller=scim_user_controller,
            action='create_user',
            conditions=dict(method=['POST']))

        mapper.connect(
            self.PATH_PREFIX + '/Users',
            controller=scim_user_controller,
            action='delete_user',
            conditions=dict(method=['DELETE']))

        # New User operations: recover password
        mapper.connect(
            '/users/{user_id}/recover_password',
            controller=spassword_controller,
            action='recover_password',
            conditions=dict(method=['GET']))

        # SNDFA User operations:
        mapper.connect(
            '/users/{user_id}/sndfa/{code}',
            controller=spassword_controller,
            action='check_sndfa_code',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/users/{user_id}/sndfa',
            controller=spassword_controller,
            action='modify_sndfa',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/users/{user_id}/checkemail',
            controller=spassword_controller,
            action='ask_for_check_email_code',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/users/{user_id}/checkemail/{code}',
            controller=spassword_controller,
            action='check_email_code',
            conditions=dict(method=['GET']))
