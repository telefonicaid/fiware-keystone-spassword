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

import time
import datetime
from oslo.utils import timeutils

from keystone.common import sql
from keystone import exception
from keystone.identity.backends.sql import User, Identity
from keystone_spassword.contrib.spassword import Driver
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

LOG = log.getLogger(__name__)


class PasswordModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'spassword'
    attributes = ['user_id', 'creation_time', 'login_attempts_among']
    user_id = sql.Column(sql.String(64), primary_key=True)
    creation_time = sql.Column(sql.DateTime(), default=None)
    login_attempts_among = sql.Column(sql.Integer, default=0)
    # bad_attempts
    extra = sql.Column(sql.JsonBlob())


class Password(Driver):

    def get_user(self, user_id):
        session = sql.get_session()
        user_ref = session.query(User).get(user_id)
        if not user_ref:
            raise exception.UserNotFound(user_id=user_id)
        return user_ref

    def set_user_creation_time(self, user):
        session = sql.get_session()
        spassword_ref = session.query(PasswordModel).get(user['id'])
        if not spassword_ref:
            data_user = {}
            data_user['user_id'] = user['id']
            data_user['creation_time'] = timeutils.utcnow()
            spassword_ref = PasswordModel.from_dict(data_user)
            with session.begin():
                session.add(spassword_ref)
        else:
            spassword_ref['creation_time'] = timeutils.utcnow()
            spassword_ref['login_attempts_among'] = 0

        return spassword_ref.to_dict()

    def update_user_modification_time(self, user):
        session = sql.get_session()
        spassword_ref = session.query(PasswordModel).get(user['id'])
        if spassword_ref:
            spassword_ref['creation_time'] = timeutils.utcnow()
        else:
            data_user = {}
            data_user['user_id'] = user['id']
            #data_user['user_name'] = user['name']
            data_user['creation_time'] = timeutils.utcnow()
            spassword_ref = PasswordModel.from_dict(data_user)
            spassword_ref['login_attempts_among'] = 0
            with session.begin():
                session.add(spassword_ref)


class Identity(Identity):
    def _check_password(self, password, user_ref):
        # Check if password has been expired
        session = sql.get_session()
        spassword_ref = session.query(PasswordModel).get(user_ref['id'])
        if not (spassword_ref == None):
            # Check password time: 2 months
            # TODO: get expiration_time from settings
            expiration_date = datetime.datetime.today() - datetime.timedelta(2*365/12)
            if (spassword_ref['creation_time'] < expiration_date):
                print "PASSWORD EXPIRED!"
                # TODO: return False ?
            
        res = super(Identity, self)._check_password(password, user_ref)
        # TODO: Reset or increase login retries
        # spassword_ref['login_attempts_among'] = 0
        return res

    # Identity interface
    def authenticate(self, user_id, password):
        res = super(Identity, self).authenticate(user_id, password)
        session = sql.get_session()
        spassword_ref = session.query(PasswordModel).get(user_id)

        if spassword_ref:
            if not res:
                spassword_ref['login_attempts_among'] += 1

            res['extras'] = {
                "password_creation_time": str(spassword_ref['creation_time']),
                "login_attempts_among": spassword_ref['login_attempts_among']
            }
        #
        # else:  # if no sspassword_ref set creation time to now() ?
        #
        return res

        
