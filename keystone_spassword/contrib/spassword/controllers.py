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


CONF = config.CONF

LOG = log.getLogger(__name__)


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
        return super(SPasswordScimUserV3Controller, self).patch_user(context,
                                                                     user_id,
                                                                     **kwargs)

    def put_user(self, context, user_id, **kwargs):
        return self.patch_user(context, user_id, **kwargs)

    def create_user(self, context, user):
        if 'password' in user:
            super(SPasswordScimUserV3Controller, self).strong_check_password(
                user['password'])

        return super(SPasswordScimUserV3Controller, self).create_user(context,
                                                                      user=user)


class SPasswordUserV3Controller(UserV3, CheckPassword):

    def __init__(self):
        super(SPasswordUserV3Controller, self).__init__()

    @controller.protected()
    def create_user(self, context, user):
        if 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).create_user(context,
                                                                  user=user)

    @controller.protected()
    def update_user(self, context, user_id, user):
        if 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).update_user(context,
                                                                  user_id=user_id,
                                                                  user=user)

    @controller.protected()
    def change_password(self, context, user_id, user):
        if 'password' in user:
            super(SPasswordUserV3Controller, self).strong_check_password(
                user['password'])
        return super(SPasswordUserV3Controller, self).change_password(context,
                                                                      user_id=user_id,
                                                                      user=user)

    def recover_password(self, context, user_id, user):
        #def recover_password(self, context, auth_payload, user_context):
        # auth_payload = {u'user': {u'domain': {u'name': u'SmartCity'}, u'password': u'password', u'name': u'adm1'}}

        """Perform user password recover procedure."""
        #user_info = password.UserAuthInfo.create(auth_payload)
        # TODO: recover user info from DB

        # Check if user has a email defined
        if not user_info.user_email:
            msg = 'User has no email defined'
            raise exception.Unauthorized(msg)

        # Create a new password randonly
        new_password = uuid.uuid4().hex

        # Set new user password
        try:
            update_dict = {'password': new_password}
            self.identity_api.update_user(context, user_id, update_dict)
            # if 'J' in versionutils.deprecated._RELEASES:
            #     self.identity_api.change_password(
            #         context,
            #         user_id=user_info.user_id,
            #         original_password=user_info.password,
            #         new_password=new_password)
            # else:
            #     self.identity_api.change_password(
            #         context,
            #         user_id=user_info.user_id,
            #         original_password=user_info.password,
            #         new_password=new_password,
            #         domain_scope=user_info.domain_id)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = 'Invalid username or password'
            raise exception.Unauthorized(msg)

        # TODO: Send email to user with new reset password
        # TODO: set mail options in plugin conf section of keystone.conf
        self.send_recovery_password_email(user_info.user_ref['email'],
                                          new_password)

    def send_recovery_password_email(self, user_email, user_password):
        import smtplib

        # SMTP_SERVER = "smtp.gmail.com"
        SMTP_SERVER = 'correo.tid.es'
        SMTP_PORT = 587
        SMTP_TLS = True

        SMTPUSER = 'iot_support@tid.es'
        PASSWORD = ''
        FROM = "iot_support@tid.es"

        # TO = [user_email] # must be a list
        TO = ["alvaro.vegagarcia@telefonica.com"]  # must be a list
        SUBJECT = "IoT Platform recovery password"
        TEXT = "Your new password is %s" % user_password

        # Prepare actual message
        mail_headers = ("From: \"%s\" <%s>\r\nTo: %s\r\n"
                        % (FROM, FROM, ", ".join(TO)))

        msg = mail_headers
        msg += ("Subject: %s\r\n\r\n" % SUBJECT)
        msg += TEXT

        # Send the mail
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo
        server.login(SMTPUSER, PASSWORD)
        server.sendmail(FROM, TO, msg)
        server.quit()
