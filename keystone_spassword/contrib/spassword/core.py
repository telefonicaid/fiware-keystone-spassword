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

from keystone.auth.plugins import password

from keystone.common import provider_api
from keystone import notifications
from keystone import exception
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log
try: from oslo_log import versionutils
except ImportError: from keystone.openstack.common import versionutils
from keystone.common import manager

LOG = log.getLogger(__name__)

try: from oslo_config import cfg
except ImportError: from oslo.config import cfg

CONF = cfg.CONF

CONF.register_opt(cfg.BoolOpt('enabled', default=False), group='spassword')
CONF.register_opt(cfg.IntOpt('pwd_exp_days', default=365), group='spassword')
CONF.register_opt(cfg.IntOpt('pwd_max_tries', default=3), group='spassword')
CONF.register_opt(cfg.IntOpt('pwd_block_minutes', default=30), group='spassword')
CONF.register_opt(cfg.ListOpt('pwd_user_blacklist'), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_server', default='0.0.0.0'), group='spassword')
CONF.register_opt(cfg.IntOpt('smtp_port', default=587), group='spassword')
CONF.register_opt(cfg.BoolOpt('smtp_tls', default=True), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_user', default='user'), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_password', default='password'), group='spassword')
CONF.register_opt(cfg.StrOpt('smtp_from', default='from'), group='spassword')
CONF.register_opt(cfg.BoolOpt('sndfa', default=False), group='spassword')
CONF.register_opt(cfg.StrOpt('sndfa_endpoint', default='localhost:5001'), group='spassword')
CONF.register_opt(cfg.IntOpt('sndfa_time_window', default=24), group='spassword')

PROVIDERS = provider_api.ProviderAPIs

RELEASES = versionutils._RELEASES if hasattr(versionutils, '_RELEASES') else versionutils.deprecated._RELEASES

Brand = 'Thinking Cities Platform'

@notifications.listener  # NOTE(dstanek): only needed if using event_callbacks
class SPasswordManager(manager.Manager):
    """SPassword Manager.

    See :mod:`keystone.common.manager.Manager` for more details on
    how this dynamically calls the backend.

    """
    driver_namespace = 'keystone.contrib.spassword'
    _provides_api = 'spassword_api'

    def __init__(self):
        LOG.debug("Manager INIT")
        self.event_callbacks = {
            # Here we add the event_callbacks class attribute that
            # calls project_deleted_callback when a project is deleted.
            notifications.ACTIONS.updated: {
                'user': [
                    self.user_updated_callback]
                },
            notifications.ACTIONS.created: {
                'user': [
                    self.user_created_callback]
                },
            notifications.ACTIONS.deleted: {
                'user': [
                    self.user_deleted_callback]
                },
            }
        super(SPasswordManager, self).__init__(
            'keystone_spassword.contrib.spassword.backends.sql.SPassword')
        LOG.debug("Manager INIT end")

    def user_updated_callback(self, service, resource_type, operation,
                              payload):
        user = self.driver.get_user(payload['resource_info'])
        LOG.debug("User %s updated." % user['id'])
        # TODO: Already is done in any update operations.
        # But only admin can modify user is password were blocked
        # Minor bug: user acount is unlocked when admin user modifies any issue
        # about user not just password
        if CONF.spassword.enabled:
            self.driver.update_user_modification_time(user)

    def user_created_callback(self, service, resource_type, operation,
                              payload):
        user = self.driver.get_user(payload['resource_info'])
        LOG.debug("User %s created." % user['id'])
        if CONF.spassword.enabled:
            user_password = self.driver.set_user_creation_time(user)

    def user_deleted_callback(self, service, resource_type, operation,
                              payload):
        user_id = payload['resource_info']
        LOG.info("User %s deleted in driver manager" % user_id)
        if CONF.spassword.enabled:
            self.driver.remove_user(user_id)

    def user_check_sndfa_code(self, user_id, code):
        LOG.info("User %s check sndfa code in driver manager" % user_id)
        return self.driver.check_sndfa_code(user_id, code)

    def user_modify_sndfa(self, user_id, enable):
        LOG.info("User %s modify sndfa in driver manager" % user_id)
        return self.driver.modify_sndfa(user_id, enable)

    def user_get_black(self, user_id):
        LOG.info("User %s get black in driver manager" % user_id)
        return self.driver.get_black(user_id)

    def user_modify_black(self, user_id, enable):
        LOG.info("User %s modify black in driver manager" % user_id)
        return self.driver.modify_black(user_id, enable)

    def user_get_pwd_expiration(self, user_id):
        LOG.info("User %s get pwd expiration in driver manager" % user_id)
        return self.driver.get_pwd_expiration(user_id)

    def user_ask_check_email_code(self, user_id):
        LOG.info("User %s ask for a check email code in driver manager" % user_id)
        # Ensure sndfa_email exists in user
        self.driver.already_email_checked(user_id)
        code = uuid.uuid4().hex[:6]
        self.driver.set_check_email_code(user_id, code)
        return code

    def user_check_email_code(self, user_id, code):
        LOG.info("User %s check email code in driver manager" % user_id)
        return self.driver.check_email_code(user_id, code)

    def already_user_check_email(self, user_id):
        LOG.info("User %s already check email in driver manager" % user_id)
        return self.driver.already_email_checked(user_id)


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

    def remove_user(self, user_id):
        """Removeuser

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

class SPassword(password.Password):

    def authenticate(self, auth_payload, user_context = None):
        """Try to authenticate against the identity backend."""
        user_info = password.auth_plugins.UserAuthInfo.create(auth_payload, 'password')

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            res = PROVIDERS.identity_api.authenticate(
                user_id=user_info.user_id,
                password=user_info.password)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = 'Invalid username or password'
            raise exception.Unauthorized(msg)

        if not user_context:
            user_context = {}

        if 'user_id' not in user_context:
            user_context['user_id'] = user_info.user_id
        if 'extras' in res:
            user_context['extras'] = res['extras']
        LOG.debug("authenticate %s" % user_context)
        if ('O' in RELEASES): # true when current version is Newton or upper
            from keystone.auth.plugins import base
            return base.AuthHandlerResponse(status=True, response_body=None,
                                            response_data=user_context)
