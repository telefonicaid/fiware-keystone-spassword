# Copyright 2012 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sqlalchemy as sql


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine
    spassword_table = sql.Table('spassword', meta, autoload=True)
    sndfa = sql.Column('sndfa', sql.Boolean(), default=False)
    sndfa_last = sql.Column('sndfa_last', sql.DateTime(), default=None)
    sndfa_code = sql.Column('sndfa_code', sql.String(32), default=None)
    sndfa_time_code = sql.Column('sndfa_time_code', sql.DateTime(), default=None)
    sndfa_email = sql.Column('sndfa_email', sql.Boolean(), default=False)
    sndfa_email_code = sql.Column('sndfa_email_code', sql.String(32), default=None)
    spassword_table.create_column(sndfa)
    spassword_table.create_column(sndfa_last)
    spassword_table.create_column(sndfa_code)
    spassword_table.create_column(sndfa_time_code)
    spassword_table.create_column(sndfa_email)
    spassword_table.create_column(sndfa_email_code)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    spassword_table = sql.Table('spassword', meta, autoload=True)
    idp_table.drop_column('sndfa')
    idp_table.drop_column('sndfa_last')
    idp_table.drop_column('sndfa_code')
    idp_table.drop_column('sndfa_time_code')
    idp_table.drop_column('sndfa_email')
    idp_table.drop_column('sndfa_email_code')
