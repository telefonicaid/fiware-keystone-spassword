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
from keystone.openstack.common import log
from keystone.openstack.common import versionutils
from keystone.common import manager
from keystone_spassword.contrib.spassword.controllers import SPasswordScimUserV3Controller
from keystone_spassword.contrib.spassword.controllers import SPasswordUserV3Controller
LOG = log.getLogger(__name__)

@dependency.provider('example_kk_api')
class Manager(manager.Manager):
    """Password Manager.

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

        super(Manager, self).__init__(
            'keystone_spassword.contrib.spassword.backends.sql.Password')

    def user_updated_callback(self, service, resource_type, operation,
                              payload):
        LOG.debug("USER_UPDATED")
        user = self.driver.get_user(payload['resource_info'])
        # TODO: Always ?
        self.driver.update_user_modification_time(user)

    def user_created_callback(self, service, resource_type, operation,
                              payload):
        LOG.debug("USER_CREATED")
        user = self.driver.get_user(payload['resource_info'])
        # print user
        user_password = self.driver.set_user_creation_time(user)


class Driver(object):
    """Interface description for Password driver."""

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


class PasswordMiddleware(wsgi.Middleware):

    def __init__(self, *args, **kwargs):
        LOG.debug("USER_CREATED")
        self.password_api = Manager()
        return super(PasswordMiddleware, self).__init__(*args, **kwargs)


class PasswordExtension(wsgi.ExtensionRouter):

    def add_routes(self, mapper):

        scim_user_controller = SPasswordScimUserV3Controller()
        user_controller = SPasswordUserV3Controller()

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
        # mapper.connect(
        #     '/users',
        #     controller=user_controller,
        #     action='create_user',
        #     conditions=dict(method=['POST']))

        # TODO: Add for create user using OS-SCIM API
        mapper.connect(
            '/OS-SCIM/Users',
            controller=scim_user_controller,
            action='create_user',
            conditions=dict(method=['POST']))


@dependency.requires('identity_api')
class SPassword(password.Password):

    def authenticate(self, context, auth_payload, user_context):
        """Try to authenticate against the identity backend."""
        user_info = password.UserAuthInfo.create(auth_payload)

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            if 'J' in versionutils.deprecated._RELEASES:
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

    def recover_password(self, context, auth_payload, user_context):
        """Perform user password recover procedure."""
        user_info = password.UserAuthInfo.create(auth_payload)

        # Check if user has a email defined
        if not user_info.user_ref['email']:
            msg = 'User has no email defined'
            raise exception.Unauthorized(msg)
        # Create a new password randonly
        new_password = uuid.uuid4().hex

        # Set new user password
        try:
            if 'J' in versionutils.deprecated._RELEASES:
                self.identity_api.change_password(
                    context,
                    user_id=user_info.user_id,
                    original_password=user_info.password,
                    new_password=new_password)
            else:
                self.identity_api.change_password(
                    context,
                    user_id=user_info.user_id,
                    original_password=user_info.password,
                    new_password=new_password,
                    domain_scope=user_info.domain_id)
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
