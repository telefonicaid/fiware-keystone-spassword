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
from keystone.common import sql
try: from oslo_utils import timeutils
except ImportError: from keystone.openstack.common import timeutils
from keystone import exception
from keystone.identity.backends.sql import User, Identity
from keystone_spassword.contrib.spassword import Driver
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log
try: from oslo.config import cfg
except ImportError: from keystone import config as cfg

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class SPasswordModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'spassword'
    attributes = ['user_id', 'user_name', 'domain_id', 'creation_time',
                  'login_attempts', 'last_login_attempt_time']
    user_id = sql.Column(sql.String(64), primary_key=True)
    user_name = sql.Column(sql.String(255), default=None)
    domain_id = sql.Column(sql.String(64), default=None)
    creation_time = sql.Column(sql.DateTime(), default=None)
    login_attempts = sql.Column(sql.Integer, default=0)
    last_login_attempt_time = sql.Column(sql.DateTime(), default=None)
    # bad_attempts
    extra = sql.Column(sql.JsonBlob())


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
            spassword_ref = SPasswordModel.from_dict(data_user)
            spassword_ref['login_attempts'] = 0
        with session.begin():
            session.add(spassword_ref)


class Identity(Identity):
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
                if (spassword_ref['creation_time'] < expiration_date):
                    LOG.warn('password of user %s %s expired ' % (user_ref['id'],
                                                                  user_ref['name']))
                    res = False
                    auth_error_msg = ('Password expired for user %s. Contact with your ' +
                                      'admin') % spassword_ref['user_name']
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
                if spassword_ref['login_attempts'] > CONF.spassword.pwd_max_tries:
                    # Check last block attempt
                    if (spassword_ref['last_login_attempt_time'] > \
                        datetime.datetime.utcnow() - \
                        datetime.timedelta(minutes=CONF.spassword.pwd_block_minutes)):
                        LOG.warn('max number of tries reach for login %s' % spassword_ref['user_name'])
                        auth_error_msg = ('Password temporarily blocked for user %s due to reach' +
                                          ' max number of tries. Contact with your ' +
                                          ' admin') % spassword_ref['user_name']
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
                if not res:
                    LOG.debug('wrong password provided at login %s' % spassword_ref['user_name'])
                    spassword_ref['login_attempts'] += 1
                else:
                    spassword_ref['login_attempts'] = 0
                    expiration_date = spassword_ref['creation_time'] + \
                        datetime.timedelta(days=CONF.spassword.pwd_exp_days)
                    res['extras'] = {
                        "password_creation_time": timeutils.isotime(spassword_ref['creation_time']),
                        "password_expiration_time": timeutils.isotime(expiration_date),
                        "pwd_user_in_blacklist": user_id in CONF.spassword.pwd_user_blacklist,
                        "last_login_attempt_time": current_attempt_time
                    }
                # Update login attempt time
                spassword_ref['last_login_attempt_time'] = current_attempt_time

            else: # User still not registered in spassword
                LOG.debug('registering in spassword %s' % user_id)
                user = self.get_user(user_id)
                data_user = {}
                data_user['user_id'] = user['id']
                data_user['user_name'] = user['name']
                data_user['domain_id'] = user['domain_id']
                data_user['creation_time'] = current_attempt_time
                data_user['last_login_attempt_time'] = current_attempt_time
                if not res:
                    data_user['login_attempts'] = 1
                else:
                    data_user['login_attempts'] = 0
                    expiration_date = data_user['creation_time'] + \
                        datetime.timedelta(days=CONF.spassword.pwd_exp_days)
                    res['extras'] = {
                        "password_creation_time": timeutils.isotime(data_user['creation_time']),
                        "password_expiration_time": timeutils.isotime(expiration_date),
                        "pwd_user_in_blacklist": user_id in CONF.spassword.pwd_user_blacklist
                    }
                spassword_ref = SPasswordModel.from_dict(data_user)

            # A new session is needed
            with session.begin():
                session.add(spassword_ref)

        if not res:
            # Return 401 due to bad user/password or user reach max attempts
            raise exception.Unauthorized(auth_error_msg)
        return res

