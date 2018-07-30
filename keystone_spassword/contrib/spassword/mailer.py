#
# Copyright 2018 Telefonica Investigacion y Desarrollo, S.A.U
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

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from keystone import exception
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

try: from oslo_config import cfg
except ImportError: from oslo.config import cfg

CONF = cfg.CONF

LOG = log.getLogger(__name__)


class SendMail(object):


    def send_email(self, to, subject, text):

        #
        # Prepare actual message
        #
        mimemsg = MIMEMultipart()
        mimemsg['From'] = CONF.spassword.smtp_from
        mimemsg['To'] = to
        mimemsg['Subject'] = subject
        body = text
        mimemsg.attach(MIMEText(body, 'plain'))
        msg = mimemsg.as_string()

        #
        # Send the mail
        #
        try:
            # TODO: server must be initialized by current object
            server = smtplib.SMTP(CONF.spassword.smtp_server,
                                  CONF.spassword.smtp_port)
        except smtplib.socket.gaierror:
            LOG.error('SMTP socket error %s %s' % (
                CONF.spassword.smtp_server, CONF.spassword.smtp_port))
            return False

        # Use tls for smtp if CONF.spassword.smtp_tls is True
        if CONF.spassword.smtp_tls:
            server.ehlo()
            server.starttls()

        # Use auth only if smtp_user and smtp_password not empty
        if CONF.spassword.smtp_user and CONF.spassword.smtp_password:
            try:
                server.login(CONF.spassword.smtp_user,
                             CONF.spassword.smtp_password)
            except smtplib.SMTPAuthenticationError:
                LOG.error('SMTP authentication error %s' % CONF.spassword.smtp_user)
                return False

        try:
            server.sendmail(CONF.spassword.smtp_from, dest, msg)
        except Exception, ex:  # try to avoid catching Exception unless you have too
            LOG.error('SMTP sendmail error %s' % ex)
            return False
        finally:
            server.quit()
        LOG.info('email was sent to %s' % dest)
        return True
