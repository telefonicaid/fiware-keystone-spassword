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

from keystone.common import controller
from keystone.common import dependency
from keystone.common import wsgi
from keystone import exception
from keystone.identity.controllers import UserV3
from keystone_scim.contrib.scim.controllers import ScimUserV3Controller
from keystone_scim.contrib.scim import converter as conv
from keystone_spassword.contrib.spassword.checker import CheckPassword
from keystone_spassword.contrib.spassword.mailer import SendMail
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

try: from oslo_config import cfg
except ImportError: from oslo.config import cfg

CONF = cfg.CONF

LOG = log.getLogger(__name__)

class SPasswordNotConfigured(exception.Error):
    message_format = "The action you have requested needs spassword configured"
    code = 400
    title = 'Not Configured'

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
        LOG.info('changing pwd of user %s spasswordusercontroller' % user_id)
        return super(SPasswordUserV3Controller, self).change_password(context,
                                                                      user_id=user_id,
                                                                      user=user)

@dependency.requires('spassword_api', 'identity_api', 'assignment_api', 'role_api')
class SPasswordV3Controller(controller.V3Controller, SendMail):

    def __init__(self):
        super(SPasswordV3Controller, self).__init__()

    def _check_spassword_configured(self):
        # Check if spassword and sndfa are enabled
        if not CONF.spassword.enabled or not CONF.spassword.sndfa:
            msg = 'SPassword was not configured or enabled'
            LOG.error('%s' % msg)
            raise SPasswordNotConfigured()

    def _check_user_has_email_defined(self, user_info):
        # Check if user has a email defined
        if not 'email' in user_info:
            msg = 'User %s %s has no email defined' % (user_info['id'],
                                                       user_info['name'])
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

    def _check_user_has_email_validated(self, user_info):
        # Check if user has a email validated
        if not self.spassword_api.already_user_check_email(user_info['id']):
            msg = 'User %s %s has no email verified' % (user_info['id'],
                                                        user_info['name'])
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

    def recover_password(self, context, user_id):
        """Perform user password recover procedure."""
        self._check_spassword_configured()
        user_info = self.identity_api.get_user(user_id)
        LOG.debug('recover password invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        self._check_user_has_email_defined(user_info)
        self._check_user_has_email_validated(user_info)

        # Create a new password randonly
        new_password = uuid.uuid4().hex[:8]

        # Set new user password
        try:
            update_dict = { 'password': new_password }
            self.identity_api.update_user(user_id, user_ref=update_dict)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = 'Invalid username or password'
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

        if self._send_recovery_password_email(user_info['email'], new_password):
            msg = 'recover password email sent to %s' % user_info['email']
            LOG.info(msg)
            return wsgi.render_response(body=msg, status=('200', 'OK'))
        else:
            msg = 'recover password email was not sent to %s' % user_info['email']
            LOG.info(msg)
            return wsgi.render_response(body=msg, status=('400', 'Error'))

    def _send_recovery_password_email(self, user_email, user_password):
        to = user_email
        subject = 'IoT Platform recovery password'
        text = 'Your new password is %s' % user_password
        return self.send_email(to, subject, text)

    def modify_sndfa(self, context, user_id, enable):
        """Perform user sndfa modification """
        self._check_spassword_configured()
        user_info = self.identity_api.get_user(user_id)
        LOG.debug('modify sndfa for user %s %s' % (user_info['id'],
                                                    user_info['name']))
        self._check_user_has_email_defined(user_info)
        self._check_user_has_email_validated(user_info)
        if (type(enable) == type(True)):
            res = self.spassword_api.user_modify_sndfa(user_id,
                                                       enable)
            response = { "modified" : res }
            return wsgi.render_response(body=response, status=('200', 'OK'))
        else:
            raise exception.ValidationError(message='invalid body format')

    # Should be called without provide an auth token
    def check_sndfa_code(self, context, user_id, code):
        """Perform user sndfa code check """
        self._check_spassword_configured()
        user_info = self.identity_api.get_user(user_id)
        LOG.debug('check sndfa code invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        self._check_user_has_email_validated(user_info)
        if self.spassword_api.user_check_sndfa_code(user_id, code):
            # Render response in HTML
            headers = [('Content-Type', 'text/html')]
            return wsgi.render_response(body="Valid code. Sndfa successfully authorized",
                                        status=('200', 'Valid code'),
                                        headers=headers)
        else:
            return wsgi.render_response(status=('401', 'No valid code. sndfa Unauthorized'))

    def ask_for_check_email_code(self, context, user_id):
        """Ask a code for user email check """
        user_info = self.identity_api.get_user(user_id)
        self._check_user_has_email_defined(user_info)
        LOG.debug('verify sndfa code invoked for user %s %s' % (user_info['id'],
                                                                user_info['name']))
        code = self.spassword_api.user_ask_check_email_code(user_id)
        to = user_info['email'] # must be a list
        subject = 'IoT Platform verify email '
        text = 'The code for verify your email is %s' % code
        if CONF.spassword.sndfa_endpoint.startswith('http'):
            link = '%s/v3/users/%s/checkemail/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        else:
            link = 'http://%s/v3/users/%s/checkemail/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        text += '\nLink is: %s' % link
        if self.send_email(to, subject, text):
            msg = 'check email code sent to %s' % user_info['email']
            LOG.info(msg)
            return wsgi.render_response(body=msg, status=('200', 'OK'))
        else:
            msg = 'check email code was not sent to %s' % user_info['email']
            LOG.info(msg)
            return wsgi.render_response(body=msg, status=('400', 'Error sending email'))

    def check_email_code(self, context, user_id, code):
        """Check a code for for user email check """
        user_info = self.identity_api.get_user(user_id)
        self._check_user_has_email_defined(user_info)
        LOG.debug('check sndfa code invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        if self.spassword_api.user_check_email_code(user_id, code):
            # Render response in HTML
            headers = [('Content-Type', 'text/html')]
            return wsgi.render_response(body="Valid code. Email sucessfully checked",
                                        status=('200', 'Valid code'),
                                        headers=headers)
        else:
            return wsgi.render_response(status=('401', 'No valid code. Email not checked'))

    def get_project_roles(self, context, user_id):
        """Get all user projects and the user roles in each project """
        user_info = self.identity_api.get_user(user_id)
        user_projects = self.assignment_api.list_projects_for_user(user_id)
        LOG.debug('projects of user %s: %s' % (user_info['id'], user_projects))
        user_project_roles = []
        for user_project in user_projects:
            LOG.debug('project %s' % (user_project))
            roles = self.assignment_api.get_roles_for_user_and_project(user_id,
                                                                       user_project['id'])
            for role in roles:
                role_ext = self.role_api.get_role(role)
                user_project_roles.append(
                    {
                        "domain": user_info['domain_id'],
                        "project": user_project['id'],
                        "project_name": user_project['name'],
                        "user": user_id,
                        "user_name": user_info["name"],
                        "role": role,
                        "role_name": role_ext["name"]
                    }
                )
        return wsgi.render_response(body=user_project_roles, status=('200', 'OK'))
