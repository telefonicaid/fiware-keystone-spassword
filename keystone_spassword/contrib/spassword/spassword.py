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
import flask
import flask_restful
from keystone.server import flask as ks_flask
from six.moves import http_client
from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone import exception
from keystone.api.users import UserResource
from keystone.api.users import UserChangePasswordResource
from keystone_scim.contrib.scim.scim import ScimUserResource
from keystone_scim.contrib.scim import converter as conv
from keystone_spassword.contrib.spassword import Brand
from keystone_spassword.contrib.spassword.checker import CheckPassword
from keystone_spassword.contrib.spassword.mailer import SendMail
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

try: from oslo_config import cfg
except ImportError: from oslo.config import cfg
from oslo_serialization import jsonutils

CONF = cfg.CONF
PROVIDERS = provider_api.ProviderAPIs
ENFORCER = rbac_enforcer.RBACEnforcer
LOG = log.getLogger(__name__)

def _build_user_target_enforcement():
    target = {}
    try:
        target['user'] = PROVIDERS.identity_api.get_user(
            flask.request.view_args.get('user_id')
        )
        if flask.request.view_args.get('group_id'):
            target['group'] = PROVIDERS.identity_api.get_group(
                flask.request.view_args.get('group_id')
            )
    except exception.NotFound:  # nosec
        # Defer existence in the event the user doesn't exist, we'll
        # check this later anyway.
        pass

    return target

class SPasswordNotConfigured(exception.Error):
    message_format = "The action you have requested needs spassword configured"
    code = 400
    title = 'Not Configured'

class SPasswordScimUserResource(ScimUserResource, CheckPassword):

    @ks_flask.unenforced_api
    def patch(self, user_id):
        user_data = self.request_body_json
        user_data = self._normalize_dict(user_data)        
        scim = self._denormalize(user_data)
        user = conv.user_scim2key(scim)
        if CONF.spassword.enabled and 'password' in user:
            try:
                super(SPasswordScimUserResource, self).strong_check_password(
                    user['password'])
            except Exception as e:
                msg = '%s' % e
                resp = flask.make_response(msg, http_client.BAD_REQUEST)
                resp.headers['Content-Type'] = 'application/json'
                return resp
        # TODO: update_user_modification_time()
        return super(SPasswordScimUserResource, self).patch(user_id)

    def put(self, user_id):
        return self.patch_(user_id)

    @ks_flask.unenforced_api
    def post(self):
        user_data = self.request_body_json
        if CONF.spassword.enabled and 'password' in user_data:
            try:
                super(SPasswordScimUserResource, self).strong_check_password(
                    user_data['password'])
            except Exception as e:
                msg = '%s' % e
                resp = flask.make_response(msg, http_client.BAD_REQUEST)
                resp.headers['Content-Type'] = 'application/json'
                return resp
        return super(SPasswordScimUserResource, self).post()

    def delete(self, user_id):
        # Delete user from spassword table
        LOG.info('deleting user %s spasswordscimusercontroller' % user_id)
        return super(SPasswordScimUserResource, self).delete(user_id)


class SPasswordUserResource(UserResource, CheckPassword):
    collection_key = 'users'
    member_key = 'user'

    @ks_flask.unenforced_api
    def post(self):
        user_data = self.request_body_json.get('user', {})
        if CONF.spassword.enabled and 'password' in user_data:
            try:
                super(SPasswordUserResource, self).strong_check_password(
                    user_data['password'])
            except Exception as e:
                msg = '%s' % e
                resp = flask.make_response(msg, http_client.BAD_REQUEST)
                resp.headers['Content-Type'] = 'application/json'
                return resp
        return super(SPasswordUserResource, self).post()

    def patch(self, user_id):
        user_data = self.request_body_json.get('user', {})
        if CONF.spassword.enabled and 'password' in user_data:
            try:
                super(SPasswordUserResource, self).strong_check_password(
                    user_data['password'])
            except Exception as e:
                raise exception.Unauthorized(
                    _('Error when changing user password: %s') % e
                )
        return super(SPasswordUserResource, self).patch(user_id)

    def delete(self, user_id):
        # Delete user from spassword table
        LOG.info('deleting user %s spasswordusercontroller' % user_id)
        return super(SPasswordUserResource, self).delete(user_id)



class SPasswordUserPasswordResource(UserChangePasswordResource, CheckPassword):
    collection_key = 'users'
    member_key = 'user'
    api_prefix = '/users'

    @ks_flask.unenforced_api
    def post(self, user_id):
        user_data = self.request_body_json.get('user', {})        
        if CONF.spassword.enabled and 'password' in user_data:
            try:
                super(SPasswordUserPasswordResource, self).strong_check_password(
                    user_data['password'])
            except Exception as e:
                msg = '%s' % e
                resp = flask.make_response(msg, http_client.BAD_REQUEST)
                resp.headers['Content-Type'] = 'application/json'
                return resp
        LOG.info('changing pwd of user %s spasswordusercontroller' % user_id)
        return super(SPasswordUserPasswordResource, self).post(user_id)


class SPasswordResource(ks_flask.ResourceBase, SendMail):
    collection_key = 'users'
    member_key = 'user'
    api_prefix = '/users'

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
        if not PROVIDERS.spassword_api.already_user_check_email(user_info['id']):
            msg = 'User %s %s has no email verified' % (user_info['id'],
                                                        user_info['name'])
            LOG.error('%s' % msg)
            raise exception.Unauthorized(msg)

class SPasswordRecoverResource(SPasswordResource):

    @ks_flask.unenforced_api
    def get(self, user_id):
        return self._recover_password(user_id)

    # Should be called without provide an auth token
    def _recover_password(self, user_id):
        """Perform user password recover procedure."""
        self._check_spassword_configured()
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('recover password procedure invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        self._check_user_has_email_defined(user_info)
        self._check_user_has_email_validated(user_info)

        code = PROVIDERS.spassword_api.user_ask_check_email_code(user_id)
        # Set email again as verified
        PROVIDERS.spassword_api.user_check_email_code(user_id, code)

        to = user_info['email'] # must be a list
        subject = Brand + ' reset password procedure '
        text = 'The reset password procedure has been started'
        if CONF.spassword.sndfa_endpoint.startswith('http'):
            link = '%s/v3/users/%s/reset_password/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        else:
            link = 'http://%s/v3/users/%s/reset_password/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        text += '\nPress in following link to complete your password reset: %s' % link
        if self.send_email(to, subject, text):
            msg = 'reset password email link sent to %s' % user_info['email']
            LOG.info(msg)
            resp = flask.make_response(msg, http_client.OK)
            resp.headers['Content-Type'] = 'application/json'
            return resp
        else:
            msg = 'reset password email link was not sent to %s' % user_info['email']
            LOG.info(msg)
            resp = flask.make_response(msg, http_client.BAD_REQUEST)
            resp.headers['Content-Type'] = 'application/json'
            return resp

class SPasswordResetResource(SPasswordResource):

    @ks_flask.unenforced_api
    def get(self, user_id, code=None):
        return self._reset_password(user_id, code)

    # Should be called without provide an auth token
    def _reset_password(self, user_id, code):
        """Perform user password reset."""

        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('reset password invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))

        if PROVIDERS.spassword_api.user_check_email_code(user_id, code):
            # Create a new password randonly
            new_password = str(uuid.uuid4())[:12]

            # Set new user password
            try:
                update_dict = { 'password': new_password }
                PROVIDERS.identity_api.update_user(user_id, user_ref=update_dict)
            except AssertionError:
                # authentication failed because of invalid username or password
                msg = 'Invalid username or password'
                LOG.error('%s' % msg)
                raise exception.Unauthorized(msg)

            resp = None;
            msg = None;
            if self._send_new_password_email(user_info['email'], new_password):
                msg = ' New password was sent by email to %s' % user_info['email']
            else:
                msg = ' New password was not sent by email to %s' % user_info['email']
            LOG.info(msg)

            # Render response in HTML
            resp = flask.make_response('Request with valid code. Password sucessfully reset.' + msg, http_client.OK)
            resp.headers['Content-Type'] = 'text/html'
            return resp            
        else:
            resp = flask.make_response('No valid code. Password not reset', http_client.UNAUTHORIZED)
            resp.headers['Content-Type'] = 'text/html'
            return resp

    def _send_new_password_email(self, user_email, user_password):
        to = user_email
        subject = Brand + ' recovery password'
        text = 'Your new password is %s, proceed to change it as soon as possible' % user_password
        return self.send_email(to, subject, text)


class SPasswordModifySndfaResource(SPasswordResource):

    def get(self, user_id):
        return self._get_sndfa(user_id)

    def post(self, user_id):
        return self._modify_sndfa(user_id)

    def _modify_sndfa(self, user_id):
        """Perform user sndfa modification """
        self._check_spassword_configured()
        enable = self.request_body_json.get('enable', False)
        ENFORCER.enforce_call(
            action='identity:update_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('modify sndfa for user %s %s' % (user_info['id'],
                                                    user_info['name']))
        self._check_user_has_email_defined(user_info)
        self._check_user_has_email_validated(user_info)
        if (type(enable) == type(True)):
            res = PROVIDERS.spassword_api.user_modify_sndfa(user_id,
                                                       enable)
            response = { "modified" : res }
            resp = flask.make_response(jsonutils.dumps(response), http_client.OK)
            resp.headers['Content-Type'] = 'application/json'
            return resp
        else:
            raise exception.ValidationError(message='invalid body format')


    def _get_sndfa(self, user_id):
        """Perform get black """
        ENFORCER.enforce_call(
            action='identity:get_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('get sndfa invoked for user %s %s' % (user_info['id'],
                                                        user_info['name']))
        sndfa = PROVIDERS.spassword_api.user_get_sndfa(user_id)
        response = { "sndfa" : sndfa }
        resp = flask.make_response(jsonutils.dumps(response), http_client.OK)
        return resp

class SPasswordCheckSndfaResource(SPasswordResource):

    @ks_flask.unenforced_api
    def get(self, user_id, code=None):
        return self._check_sndfa_code(user_id, code)

    # Should be called without provide an auth token
    def _check_sndfa_code(self, user_id, code):
        """Perform user sndfa code check """
        self._check_spassword_configured()
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('check sndfa code invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        self._check_user_has_email_validated(user_info)
        if PROVIDERS.spassword_api.user_check_sndfa_code(user_id, code):
            # Render response in HTML
            resp = flask.make_response('Valid code. Sndfa successfully authorized', http_client.OK)
            resp.headers['Content-Type'] = 'text/html'
            return resp
        else:
            resp = flask.make_response('No valid code. sndfa Unauthorized', http_client.UNAUTHORIZED)
            resp.headers['Content-Type'] = 'application/json'
            return resp


class SPasswordAskCheckEmailResource(SPasswordResource):

    def get(self, user_id):
        return self._ask_for_check_email_code(user_id)

    def _ask_for_check_email_code(self, user_id):
        """Ask a code for user email check """
        ENFORCER.enforce_call(
            action='identity:update_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        self._check_user_has_email_defined(user_info)
        LOG.debug('verify sndfa code invoked for user %s %s' % (user_info['id'],
                                                                user_info['name']))
        code = PROVIDERS.spassword_api.user_ask_check_email_code(user_id)
        to = user_info['email'] # must be a list
        subject = Brand + ' verify email '
        text = 'The code for verify your email is %s' % code
        if CONF.spassword.sndfa_endpoint.startswith('http'):
            link = '%s/v3/users/%s/checkemail/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        else:
            link = 'http://%s/v3/users/%s/checkemail/%s' % (CONF.spassword.sndfa_endpoint, user_info['id'], code)
        text += '\nLink is: %s' % link
        if self.send_email(to, subject, text):
            msg = 'check email code sent to %s' % user_info['email']
            LOG.info(msg)
            resp = flask.make_response(msg, http_client.OK)
            resp.headers['Content-Type'] = 'application/json'
            return resp
        else:
            msg = 'check email code was not sent to %s' % user_info['email']
            LOG.info(msg)
            resp = flask.make_response(msg, http_client.BAD_REQUEST)
            resp.headers['Content-Type'] = 'application/json'
            return resp

class SPasswordCheckEmailResource(SPasswordResource):

    @ks_flask.unenforced_api
    def get(self, user_id, code=None):
        return self._check_email_code(user_id, code)

    # Should be called without provide an auth token
    def _check_email_code(self, user_id, code):
        """Check a code for for user email check """
        user_info = PROVIDERS.identity_api.get_user(user_id)
        self._check_user_has_email_defined(user_info)
        LOG.debug('check sndfa code invoked for user %s %s' % (user_info['id'],
                                                               user_info['name']))
        if PROVIDERS.spassword_api.user_check_email_code(user_id, code):
            # Render response in HTML
            resp = flask.make_response('Valid code. Email sucessfully checked', http_client.OK)
            resp.headers['Content-Type'] = 'text/html'
            return resp            
        else:
            resp = flask.make_response('No valid code. Email not checked', http_client.UNAUTHORIZED)
            resp.headers['Content-Type'] = 'application/json'
            return resp


class SPasswordUserProjectRolesResource(SPasswordUserResource):

    def get(self, user_id):
        """Get all user projects and the user roles in each project """
        ENFORCER.enforce_call(
            action='identity:get_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        user_projects = PROVIDERS.assignment_api.list_projects_for_user(user_id)
        LOG.debug('projects of user %s: %s' % (user_info['id'], user_projects))
        user_project_roles = []
        for user_project in user_projects:
            LOG.debug('project %s' % (user_project))
            roles = PROVIDERS.assignment_api.get_roles_for_user_and_project(user_id,
                                                                       user_project['id'])
            for role in roles:
                role_ext = PROVIDERS.role_api.get_role(role)
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
        resp = flask.make_response(jsonutils.dumps(user_project_roles), http_client.OK)
        resp.headers['Content-Type'] = 'application/json'
        return resp        

class SPasswordModifyBlackResource(SPasswordResource):

    def get(self, user_id):
        return self._get_black(user_id)

    def post(self, user_id):
        return self._modify_black(user_id)

    def _modify_black(self, user_id):
        """Perform user black list membership modification """
        self._check_spassword_configured()
        enable = self.request_body_json.get('enable', False)
        ENFORCER.enforce_call(
            action='identity:update_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('modify black list membership for user %s %s' % (user_info['id'],
                                                    user_info['name']))

        if (type(enable) == type(True)):
            res = PROVIDERS.spassword_api.user_modify_black(user_id,
                                                            enable)
            response = { "modified" : res }
            resp = flask.make_response(jsonutils.dumps(response), http_client.OK)
            resp.headers['Content-Type'] = 'application/json'
            return resp
        else:
            raise exception.ValidationError(message='invalid body format')

    def _get_black(self, user_id):
        """Perform get black """
        ENFORCER.enforce_call(
            action='identity:get_user',
            build_target=_build_user_target_enforcement
        )
        user_info = PROVIDERS.identity_api.get_user(user_id)
        LOG.debug('get black invoked for user %s %s' % (user_info['id'],
                                                        user_info['name']))
        black = PROVIDERS.spassword_api.user_get_black(user_id)
        pwd_expiration = PROVIDERS.spassword_api.user_get_pwd_expiration(user_id)
        response = { "black" : black,
                     "pwd_expiration_time": pwd_expiration}
        resp = flask.make_response(jsonutils.dumps(response), http_client.OK)
        return resp

class SPasswordAPI(ks_flask.APIBase):
    _name = 'spassword'
    _import_name = __name__
    api_url_prefix = '/'
    resources = [SPasswordUserResource]

    resource_mapping = [
        ks_flask.construct_resource_map(
            resource=SPasswordScimUserResource,
            url='/OS-SCIM/Users/<string:user_id>',
            resource_kwargs={},
            rel='spassword-user-scim',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordUserPasswordResource,
            url='/users/<string:user_id>/password',
            resource_kwargs={},
            rel='user_change_password',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordRecoverResource,
            url='/users/<string:user_id>/recover_password',
            resource_kwargs={},
            rel='recover_password',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordResetResource,
            url='/users/<string:user_id>/reset_password/<string:code>',
            resource_kwargs={},
            rel='recover_password',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordModifySndfaResource,
            url='/users/<string:user_id>/sndfa',
            resource_kwargs={},
            rel='sndfa',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordCheckSndfaResource,
            url='/users/<string:user_id>/sndfa/<string:code>',
            resource_kwargs={},
            rel='sndfa',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordAskCheckEmailResource,
            url='/users/<string:user_id>/checkemail',
            resource_kwargs={},
            rel='email',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordCheckEmailResource,
            url='/users/<string:user_id>/checkemail/<string:code>',
            resource_kwargs={},
            rel='email',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordUserProjectRolesResource,
            url='/users/<string:user_id>/project_roles',
            resource_kwargs={},
            rel='get_project_roles',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        ),
        ks_flask.construct_resource_map(
            resource=SPasswordModifyBlackResource,
            url='/users/<string:user_id>/black',
            resource_kwargs={},
            rel='black',
            path_vars={'user_id': json_home.Parameters.USER_ID}
        )
    ]


APIs = (SPasswordAPI,)
