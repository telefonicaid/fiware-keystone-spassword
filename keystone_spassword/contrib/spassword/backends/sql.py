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

import datetime
import uuid

from keystone.common import sql
from keystone.common import dependency
try: from oslo_utils import timeutils
except ImportError: from keystone.openstack.common import timeutils
from keystone import exception
from keystone.identity.backends.sql import User, Identity
from keystone_spassword.contrib.spassword import Driver
from keystone_spassword.contrib.spassword.mailer import SendMail
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log
try: from oslo.config import cfg
except ImportError: from keystone import config as cfg

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class SPasswordSecurityError(exception.Error):
    def _build_message(self, message, **kwargs):
        return '%(message)s' % {
            'message': message or self.message_format % kwargs}


class SPasswordUnauthorized(SPasswordSecurityError):
    message_format = "The request you have made requires authentication."
    code = 401
    title = 'Unauthorized'


class SPasswordModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'spassword'
    attributes = ['user_id', 'user_name', 'domain_id', 'creation_time',
                  'login_attempts', 'last_login_attempt_time',
                  'sndfa', 'sndfa_last', 'sndfa_code', 'sndfa_time_code',
                  'sndfa_email', 'sndfa_email_code'
                  ]
    user_id = sql.Column(sql.String(64), primary_key=True)
    user_name = sql.Column(sql.String(255), default=None)
    domain_id = sql.Column(sql.String(64), default=None)
    creation_time = sql.Column(sql.DateTime(), default=None)
    login_attempts = sql.Column(sql.Integer, default=0)
    last_login_attempt_time = sql.Column(sql.DateTime(), default=None)
    # bad_attempts
    extra = sql.Column(sql.JsonBlob())
    # sndfa
    sndfa = sql.Column(sql.Boolean(), default=False)
    sndfa_last = sql.Column(sql.DateTime(), default=None)
    sndfa_code = sql.Column(sql.String(32), default=None)
    sndfa_time_code = sql.Column(sql.DateTime(), default=None)
    sndfa_email = sql.Column(sql.Boolean(), default=False)
    sndfa_email_code = sql.Column(sql.String(32), default=None)



class SPassword(Driver):

    def get_user(self, user_id):
        session = sql.get_session()
        user_ref = session.query(User).get(user_id)
        if not user_ref:
            raise exception.UserNotFound(user_id=user_id)
        return user_ref

    def remove_user(self, user_id):
        session = sql.get_session()
        LOG.info('removing user %s from spassword' % user_id)
        spassword_ref = session.query(SPasswordModel).get(user_id)
        if spassword_ref:
            with session.begin():
                session.delete(spassword_ref)

    def set_user_creation_time(self, user):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user['id'])
        LOG.debug('set user creation time for %s' % user['id'])
        if not spassword_ref:
            data_user = {}
            data_user['user_id'] = user['id']
            data_user['user_name'] = user['name']
            data_user['creation_time'] = datetime.datetime.utcnow()
            data_user['domain_id'] = user['domain_id']
            data_user['sndfa'] = False
            data_user['sndfa_last'] = None
            data_user['sndfa_code'] = None
            data_user['sndfa_time_code'] = None
            data_user['sndfa_email'] = False
            data_user['sndfa_email_code'] = None
            spassword_ref = SPasswordModel.from_dict(data_user)
        else:
            # TODO: Never reached?
            LOG.info('user %s already created in spassword, just updating' % user['id'])
            spassword_ref['creation_time'] = datetime.datetime.utcnow()
            spassword_ref['login_attempts'] = 0

        # A new session is needed
        with session.begin():
            session.add(spassword_ref)

        return spassword_ref.to_dict()

    def update_user_modification_time(self, user):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user['id'])
        LOG.debug('update user modification time for %s' % user['id'])
        if spassword_ref:
            spassword_ref['creation_time'] = datetime.datetime.utcnow()
            spassword_ref['login_attempts'] = 0
        else:
            data_user = {}
            data_user['user_id'] = user['id']
            data_user['user_name'] = user['name']
            data_user['domain_id'] = user['domain_id']
            data_user['creation_time'] = datetime.datetime.utcnow()
            data_user['sndfa'] = False
            data_user['sndfa_last'] = None
            data_user['sndfa_code'] = None
            data_user['sndfa_time_code'] = None
            data_user['sndfa_email'] = False
            data_user['sndfa_email_code'] = None
            spassword_ref = SPasswordModel.from_dict(data_user)
            spassword_ref['login_attempts'] = 0
        with session.begin():
            session.add(spassword_ref)

    # Second Factor Auth methods
    #
    def set_user_sndfa_code(self, user, newcode):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user['id'])
        LOG.debug('set user sndfa code %s for user %s' % (newcode, user['id']))
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if 'sndfa' in spassword:
                if spassword['sndfa'] and spassword['sndfa_email']:
                    spassword_ref['sndfa_time_code'] = datetime.datetime.utcnow()
                    spassword_ref['sndfa_code'] = newcode
                    with session.begin():
                        session.add(spassword_ref)
                else:
                    LOG.warn('user %s still has not sndfa enabled or email verified' % user['id'])
            else:
                data_user = {}
                data_user['sndfa'] = False
                data_user['sndfa_last'] = None
                data_user['sndfa_code'] = None
                data_user['sndfa_time_code'] = None
                data_user['sndfa_email'] = False
                data_user['sndfa_email_code'] = None
                spassword_ref = SPasswordModel.from_dict(data_user)
                with session.begin():
                    session.add(spassword_ref)
        else:
            LOG.warn('user %s still has not spassword data' % user['id'])

    def modify_sndfa(self, user_id, enable):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user_id)
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if spassword['sndfa_email']:
                spassword_ref['sndfa'] = enable
                with session.begin():
                    session.add(spassword_ref)
                return True
            else:
                LOG.warn('user %s still has not sndfa enabled or email verified' % user_id)
        else:
            LOG.warn('user %s still has not spassword data' % user_id)
        return False

    def check_sndfa_code(self, user_id, code):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user_id)
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if spassword['sndfa'] and spassword['sndfa_email']:
                checked = spassword['sndfa_code'] == code
                if checked:
                    spassword_ref['sndfa_last'] = datetime.datetime.utcnow()
                    with session.begin():
                        session.add(spassword_ref)
                return checked
            else:
                LOG.warn('user %s still has not sndfa enabled or email verified' % user_id)
        else:
            LOG.warn('user %s still has not spassword data' % user_id)
        return False

    def already_sndfa_signed(self, user):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user['id'])
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if spassword['sndfa'] and spassword['sndfa_email']:
                if (spassword['sndfa_last'] and
                        spassword['sndfa_last'] < datetime.datetime.utcnow() + \
                        datetime.timedelta(hours=CONF.spassword.sndfa_time_window)):
                    LOG.debug('user %s sndfa verified' % user['id'])
                    return True
                else:
                    LOG.debug('user %s sndfa expired' % user['id'])
        else:
            LOG.warn('user %s still has not spassword data' % user['id'])
        return False

    def set_check_email_code(self, user_id, newcode):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user_id)
        if spassword_ref:
            spassword_ref['sndfa_email_code'] = newcode
            spassword_ref['sndfa_email'] = False
            with session.begin():
                session.add(spassword_ref)
        else:
            LOG.warn('user %s still has not spassword data' % user_id)

    def check_email_code(self, user_id, code):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user_id)
        check = False
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if spassword['sndfa_email_code']:
                LOG.debug('check email code user_id %s code %s sndfa_email_code %s ' % (user_id, code, spassword['sndfa_email_code']))
                check = spassword['sndfa_email_code'] == code
                spassword_ref['sndfa_email'] = check
                with session.begin():
                    session.add(spassword_ref)
        else:
            LOG.warn('user %s still has not spassword data' % user_id)
        return check

    def already_email_checked(self, user_id):
        session = sql.get_session()
        spassword_ref = session.query(SPasswordModel).get(user_id)
        if spassword_ref:
            spassword = spassword_ref.to_dict()
            if 'sndfa_email' in spassword:
                return spassword['sndfa_email']
            else:
                LOG.warn('user %s still has not sndfa_email data' % user_id)
                data_user = {}
                data_user['sndfa'] = False
                data_user['sndfa_last'] = None
                data_user['sndfa_code'] = None
                data_user['sndfa_time_code'] = None
                data_user['sndfa_email'] = False
                data_user['sndfa_email_code'] = None
                spassword_ref = SPasswordModel.from_dict(data_user)
                with session.begin():
                    session.add(spassword_ref)
        else:
            LOG.warn('user %s still has not spassword data' % user_id)
        return False

@dependency.requires('spassword_api')
class Identity(Identity, SendMail):
    def _check_password(self, password, user_ref):
        if CONF.spassword.enabled:
            # Check if password has been expired
            session = sql.get_session()
            spassword_ref = session.query(SPasswordModel).get(user_ref['id'])
            if (not (spassword_ref == None)) and \
                (not user_ref['id'] in CONF.spassword.pwd_user_blacklist):
                # Check password time
                expiration_date = datetime.datetime.utcnow() - \
                  datetime.timedelta(days=CONF.spassword.pwd_exp_days)
                spassword = spassword_ref.to_dict()
                if (spassword['creation_time'] < expiration_date):
                    LOG.warn('password of user %s %s expired ' % (user_ref['id'],
                                                                  user_ref['name']))
                    res = False
                    auth_error_msg = ('Password expired for user %s. Contact with your ' +
                                      'admin') % spassword['user_name']
                    raise exception.Unauthorized(auth_error_msg)

        res = super(Identity, self)._check_password(password, user_ref)
        return res

    # Identity interface
    def authenticate(self, user_id, password):

        if CONF.spassword.enabled and \
           not (user_id in CONF.spassword.pwd_user_blacklist):
            session = sql.get_session()
            spassword_ref = session.query(SPasswordModel).get(user_id)

            if spassword_ref:
                spassword = spassword_ref.to_dict()
                if spassword['login_attempts'] > CONF.spassword.pwd_max_tries:
                    # Check last block attempt
                    if (spassword['last_login_attempt_time'] > \
                        datetime.datetime.utcnow() - \
                        datetime.timedelta(minutes=CONF.spassword.pwd_block_minutes)):
                        LOG.warn('max number of tries reach for login %s' % spassword['user_name'])
                        auth_error_msg = ('Password temporarily blocked for user %s due to reach' +
                                          ' max number of tries. Contact with your ' +
                                          ' admin') % spassword['user_name']
                        raise exception.Unauthorized(auth_error_msg)
        try:
            res = super(Identity, self).authenticate(user_id, password)
        except AssertionError:
            res = False
            auth_error_msg = 'Invalid username or password'

        if CONF.spassword.enabled:
            session = sql.get_session()
            spassword_ref = session.query(SPasswordModel).get(user_id)
            current_attempt_time = datetime.datetime.utcnow()

            if spassword_ref:
                spassword = spassword_ref.to_dict()
                if not res:
                    LOG.debug('wrong password provided at login %s' % spassword['user_name'])
                    spassword_ref['login_attempts'] += 1
                else:
                    spassword_ref['login_attempts'] = 0
                    expiration_date = spassword_ref['creation_time'] + \
                        datetime.timedelta(days=CONF.spassword.pwd_exp_days)
                    res['extras'] = {
                        "password_creation_time": timeutils.isotime(spassword['creation_time']),
                        "password_expiration_time": timeutils.isotime(expiration_date),
                        "pwd_user_in_blacklist": user_id in CONF.spassword.pwd_user_blacklist,
                        "last_login_attempt_time": spassword['last_login_attempt_time']
                    }
                # Update login attempt time
                spassword_ref['last_login_attempt_time'] = current_attempt_time

                # Check if sndfa_email in user
                if res and CONF.spassword.sndfa and 'sndfa_email' in spassword:
                    # Put sndfa and sndfa_email info
                    res['extras']['sndfa_email'] = spassword['sndfa_email']
                # Check if sndfa in user
                if res and CONF.spassword.sndfa and 'sndfa' in spassword and spassword['sndfa']:
                    # Put sndfa and sndfa_email info
                    res['extras']['sndfa'] = spassword['sndfa']
                    if spassword['sndfa_email']:
                        if (spassword['sndfa_last'] and
                                spassword['sndfa_last'] > datetime.datetime.utcnow() - \
                                datetime.timedelta(hours=CONF.spassword.sndfa_time_window)):
                            LOG.debug('user %s was already validated with 2fa' % user_id)
                        else:
                            # Should retry code that was sent email
                            LOG.debug('user %s was not validated with 2fa due to code' % user_id)
                            if (spassword['sndfa_time_code'] and
                                    spassword['sndfa_time_code'] > datetime.datetime.utcnow() - \
                                    datetime.timedelta(hours=CONF.spassword.sndfa_time_window)):
                                code = spassword['sndfa_code']
                            else:
                                code = uuid.uuid4().hex[:6]
                                self.spassword_api.set_user_sndfa_code(self.get_user(user_id), code)
                            to = self.get_user(user_id)['email']
                            subject = 'IoT Platform second factor auth procedure'
                            text = 'The code for verify your access is %s' % code
                            link = 'http://%s/v3/users/%s/sndfa/%s' % (CONF.spassword.sndfa_endpoint, user_id, code)
                            text += ' Link to verify your access is: %s' % link
                            self.send_email(to, subject, text)
                            res = None
                            auth_error_msg = 'Expecting Second Factor Authentication, email was sent. '
                            auth_error_msg += 'Please check it and click in provided link.'
                    else:
                        # Should return that emails is not validated
                        LOG.debug('user %s was not validated with 2fa due to email not verified' % user_id)
                        # TODO: force email code verification ?
                        res = None
                        auth_error_msg = 'Email not verificated to perform Second Factor Authentication. '
                        auto_error_msg += 'Please contact with your admin to solve it.'

            else: # User still not registered in spassword
                LOG.debug('registering in spassword %s' % user_id)
                user = self.get_user(user_id)
                data_user = {}
                data_user['user_id'] = user['id']
                data_user['user_name'] = user['name']
                data_user['domain_id'] = user['domain_id']
                data_user['creation_time'] = current_attempt_time
                data_user['last_login_attempt_time'] = current_attempt_time
                data_user['sndfa'] = False
                data_user['sndfa_last'] = None
                data_user['sndfa_code'] = None
                data_user['sndfa_time_code'] = None
                data_user['sndfa_email'] = False
                data_user['sndfa_email_code'] = None
                if not res:
                    data_user['login_attempts'] = 1
                else:
                    data_user['login_attempts'] = 0
                    expiration_date = data_user['creation_time'] + \
                        datetime.timedelta(days=CONF.spassword.pwd_exp_days)
                    res['extras'] = {
                        "password_creation_time": timeutils.isotime(data_user['creation_time']),
                        "password_expiration_time": timeutils.isotime(expiration_date),
                        "pwd_user_in_blacklist": user_id in CONF.spassword.pwd_user_blacklist,
                        "sndfa" : False,
                        "sndfa_email" : False
                    }
                spassword_ref = SPasswordModel.from_dict(data_user)

            # A new session is needed
            with session.begin():
                session.add(spassword_ref)

        if not res:
            # Return 401 due to bad user/password or user reach max attempts
            raise SPasswordUnauthorized(auth_error_msg)
        return res

