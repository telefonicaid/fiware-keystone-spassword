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

import uuid

from keystone import auth
from keystone.auth.plugins import password
from keystone.common import dependency
from keystone.common import extension
from keystone.common import wsgi
from keystone import exception
from keystone import identity
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log
from keystone.openstack.common import versionutils
from keystone.common import manager
from keystone_spassword.contrib.spassword.controllers import SPasswordScimUserV3Controller
from keystone_spassword.contrib.spassword.controllers import SPasswordUserV3Controller
LOG = log.getLogger(__name__)


from oslo.config import cfg
CONF = cfg.CONF
CONF.register_opt(cfg.BoolOpt('enabled', default=False), group='spassword')
CONF.register_opt(cfg.IntOpt('pwd_exp_days', default=365), group='spassword')
CONF.register_opt(cfg.IntOpt('pwd_max_tries', default=3), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_server', default='0.0.0.0'), group='spassword')
CONF.register_opt(cfg.IntOpt('smtp_port', default=587), group='spassword')
CONF.register_opt(cfg.BoolOpt('smtp_tls', default=True), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_user', default='user'), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_password', default='password'), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_from', default='from'), group='spassword')


@dependency.provider('spassword_api')
class SPasswordManager(manager.Manager):
    """SPassword Manager.

    See :mod:`keystone.common.manager.Manager` for more details on
    how this dynamically calls the backend.

    """

    def __init__(self):
        LOG.debug("Manager INIT")
        self.event_callbacks = {
            # Here we add the event_callbacks class attribute that
            # calls project_deleted_callback when a project is deleted.
            'updated': {
                'user': [
                    self.user_updated_callback]
                },
            'created': {
                'user': [
                    self.user_created_callback]
                },
            }

        super(SPasswordManager, self).__init__(
            'keystone_spassword.contrib.spassword.backends.sql.SPassword')

    def user_updated_callback(self, service, resource_type, operation,
                              payload):
        LOG.debug("USER_UPDATED")
        user = self.driver.get_user(payload['resource_info'])
        # TODO: Always ?
        if CONF.spassword.enabled:
            self.driver.update_user_modification_time(user)

    def user_created_callback(self, service, resource_type, operation,
                              payload):
        LOG.debug("USER_CREATED")
        user = self.driver.get_user(payload['resource_info'])
        # print user
        if CONF.spassword.enabled:
            user_password = self.driver.set_user_creation_time(user)


class Driver(object):
    """Interface description for SPassword driver."""

    def get_user(self, user_id):
        """Getuser

        :param data: example data
        :type data: string
        :raises: keystone.exception,
        :returns: None.

        """
        raise exception.NotImplemented()

    def set_user_creation_time(self, user):
        """Setuser

        :param data: example data
        :type data: string
        :raises: keystone.exception,
        :returns: None.

        """
        raise exception.NotImplemented()

    def update_user_modification_time(self, user):
        """Setuser

        :param data: example data
        :type data: string
        :raises: keystone.exception,
        :returns: None.

        """
        raise exception.NotImplemented()


class SPasswordMiddleware(wsgi.Middleware):

    def __init__(self, *args, **kwargs):
        LOG.debug("SPasswordMiddleware INIT")
        try:
            self.spassword_api = SPasswordManager()
        except Exception:
            LOG.debug("SPasswordMiddleware already registered")
        return super(SPasswordMiddleware, self).__init__(*args, **kwargs)


@dependency.requires('identity_api')
class SPassword(password.Password):

    def authenticate(self, context, auth_payload, user_context):
        """Try to authenticate against the identity backend."""
        if ('L' in versionutils.deprecated._RELEASES):
            user_info = password.auth_plugins.UserAuthInfo.create(auth_payload, self.method)
        else:
            user_info = password.UserAuthInfo.create(auth_payload)

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            if (('J' in versionutils.deprecated._RELEASES) or
                ('K' in versionutils.deprecated._RELEASES)):
                res = self.identity_api.authenticate(
                    context,
                    user_id=user_info.user_id,
                    password=user_info.password)
            else:
                res = self.identity_api.authenticate(
                    context,
                    user_id=user_info.user_id,
                    password=user_info.password,
                    domain_scope=user_info.domain_id)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = 'Invalid username or password'
            raise exception.Unauthorized(msg)

        if 'user_id' not in user_context:
            user_context['user_id'] = user_info.user_id
        if 'extras' in res:
            user_context['extras'] = res['extras']
