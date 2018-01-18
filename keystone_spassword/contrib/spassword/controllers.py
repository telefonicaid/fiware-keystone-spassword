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
from keystone_spassword.contrib.spassword.checker import CheckPassword
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

try: from oslo_config import cfg
except ImportError: from oslo.config import cfg

CONF = cfg.CONF

LOG = log.getLogger(__name__)


class SPasswordScimUserV3Controller(ScimUserV3Controller, CheckPassword):

    def __init__(self):
        super(SPasswordScimUserV3Controller, self).__init__()

    def patch_user(self, context, user_id, **kwargs):
        scim = self._denormalize(kwargs)
        user = conv.user_scim2key(scim)
        if CONF.spassword.enabled and 'password' in user:
            super(SPasswordScimUserV3Controller, self).strong_check_password(
                user['password'])

        # TODO: update_user_modification_time()
        return super(SPasswordScimUserV3Controller, self).patch_user(context,
                                                                     user_id,
                                                                     **kwargs)

    def put_user(self, context, user_id, **kwargs):
        return self.patch_user(context, user_id, **kwargs)

    def create_user(self, context, user):
        if CONF.spassword.enabled and 'password' in user:
            super(SPasswordScimUserV3Controller, self).strong_check_password(
                user['password'])

        return super(SPasswordScimUserV3Controller, self).create_user(context,
                                                                      user=user)
    def delete_user(self, context, user_id):
        # Delete user from spassword table
        LOG.info('deleting user %s spasswordscimusercontroller' % user_id)
        return super(SPasswordScimUserV3Controller, self).delete_user(context,
                                                                      user_id)


#@dependency.requires('spassword_api')
class SPasswordUserV3Controller(UserV3, CheckPassword):

    def __init__(self):
        super(SPasswordUserV3Controller, self).__init__()

    @controller.protected()
    def create_user(self, context, user):
        if CONF.spassword.enabled and 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).create_user(context,
                                                                  user=user)

    @controller.protected()
    def update_user(self, context, user_id, user):
        if CONF.spassword.enabled and 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).update_user(context,
                                                                  user_id=user_id,
                                                                  user=user)
    @controller.protected()
    def delete_user(self, context, user_id):
        # Delete user from spassword table
        LOG.info('deleting user %s spasswordusercontroller' % user_id)
        return super(SPasswordUserV3Controller, self).delete_user(context,
                                                                  user_id=user_id)

    @controller.protected()
    def change_password(self, context, user_id, user):
        if CONF.spassword.enabled and 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).change_password(context,
                                                                      user_id=user_id,
                                                                      user=user)

    def recover_password(self, context, user_id):
        """Perform user password recover procedure."""

        if not CONF.spassword.enabled:
            raise exception.NotImplemented()

        user_info = self.identity_api.get_user(user_id)
        LOG.debug('recover password invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))

        # Check if user has a email defined
        if not 'email' in user_info:
            msg = 'User %s %s has no email defined' % (user_info['id'],
                                                       user_info['name'])
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

        # Create a new password randonly
        new_password = uuid.uuid4().hex

        # Set new user password
        try:
            update_dict = {'password': new_password}
            self.identity_api.update_user( user_id, user_ref=update_dict)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = 'Invalid username or password'
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

        self.send_recovery_password_email(user_info['email'],
                                          new_password)

    def send_recovery_password_email(self, user_email, user_password):
        import smtplib

        TO = [user_email] # must be a list
        SUBJECT = "IoT Platform recovery password"
        TEXT = "Your new password is %s" % user_password

        #
        # Prepare actual message
        #
        mail_headers = ("From: \"%s\" <%s>\r\nTo: %s\r\n"
                        % (CONF.spassword.smtp_from,
                           CONF.spassword.smtp_from,
                           ", ".join(TO)))

        msg = mail_headers
        msg += ("Subject: %s\r\n\r\n" % SUBJECT)
        msg += TEXT

        #
        # Send the mail
        #
        try:
            server = smtplib.SMTP(CONF.spassword.smtp_server,
                                  CONF.spassword.smtp_port)
        except smtplib.socket.gaierror:
            LOG.error('SMTP socket error')
            return False

        server.ehlo()
        server.starttls()
        server.ehlo

        try:
            server.login(CONF.spassword.smtpuser,
                         CONF.spassword.smtppassword)
        except smtplib.SMTPAuthenticationError:
            LOG.error('SMTP autentication error')
            return False

        try:
            server.sendmail(CONF.spassword.smtp_from, TO, msg)
        except Exception:  # try to avoid catching Exception unless you have too
            LOG.error('SMTP autentication error')
            return False
        finally:
            server.quit()

        LOG.info('recover password email sent to %s' % user_email)


    # def check_sndfa_code(self, context, user_id, code):
    #     """Perform user sndfa code check """

    #     if CONF.spassword.enabled and CONF.spassword.sndfa_enabled:
    #         user_info = self.identity_api.get_user(user_id)
    #         LOG.debug('check sndfa code invoked for user %s %s' % (user_info['id'],
    #                                                               user_info['name']))
    #         res = self.spassword_api.user_check_sndfa_code(user_id, code)
    #         LOG.debug('result %s' % res);
    #         # TODO  ?

    # def ask_for_check_email_code(self, context, user_id):
    #     """Ask a code for user email check """

    #     if CONF.spassword.enabled and CONF.spassword.sndfa_enabled:
    #         user_info = self.identity_api.get_user(user_id)
    #         LOG.debug('verify sndfa code invoked for user %s %s' % (user_info['id'],
    #                                                               user_info['name']))
    #         res = self.spassword_api.user_ask_check_email_code(user_id)
    #         LOG.debug('result %s' % res);
    #         # TODO  ?

    # def check_email_code(self, context, user_id, code):
    #     """Check a code for for user email check """

    #     if CONF.spassword.enabled and CONF.spassword.sndfa_enabled:
    #         user_info = self.identity_api.get_user(user_id)
    #         LOG.debug('verify sndfa code invoked for user %s %s' % (user_info['id'],
    #                                                               user_info['name']))
    #         res = self.spassword_api.user_check_email_code(user_id, code)
    #         LOG.debug('result %s' % res);
    #         # TODO  ?
