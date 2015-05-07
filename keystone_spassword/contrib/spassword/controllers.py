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

"""Extensions supporting Strong Passwords."""

import copy
import uuid

from keystone import config
from keystone.common import controller
from keystone.common import dependency
from keystone.common import extension
from keystone.common import wsgi
from keystone import exception
from keystone import identity
from keystone.identity.controllers import UserV3
from keystone_scim.contrib.scim.controllers import ScimUserV3Controller
from keystone_scim.contrib.scim import converter as conv
from keystone.openstack.common import log


CONF = config.CONF

LOG = log.getLogger(__name__)


class CheckPassword(object):

    def strong_check_password(self, new_password):
        # Check password strengh
        try:
            import cracklib
            try:
                cracklib.VeryFascistCheck(new_password)
            except ValueError, msg:
                raise exception.ValidationError(target='user',
                        attribute='The password is too weak ({0})'.format(msg))
        except ImportError:  # not used if not configured (dev environments)
            LOG.error('cracklib module is not properly configured, '
                        'weak password can be used when changing')


class SPasswordScimUserV3Controller(ScimUserV3Controller, CheckPassword):

    def __init__(self):
        super(SPasswordScimUserV3Controller, self).__init__()

    def patch_user(self, context, user_id, **kwargs):
        scim = self._denormalize(kwargs)
        user = conv.user_scim2key(scim)
        if 'password' in user:
            super(SPasswordScimUserV3Controller, self).strong_check_password(
                user['password'])

        # TODO: update_user_modification_time()
        return super(SPasswordScimUserV3Controller, self).patch_user(context, user_id, **kwargs)
    
    def put_user(self, context, user_id, **kwargs):
        return self.patch_user(context, user_id, **kwargs)

    def create_user(self, context, user):
        if 'password' in user:
            super(SPasswordScimUserV3Controller, self).strong_check_password(
                user['password'])

        return super(SPasswordScimUserV3Controller, self).create_user(context,
                                                                      user)


class SPasswordUserV3Controller(UserV3, CheckPassword):

    def __init__(self):
        super(SPasswordUserV3Controller, self).__init__()

    def create_user(self, context, user):
        if 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])

        return super(SPasswordUserV3Controller, self).create_user(context,
                                                                  user)
