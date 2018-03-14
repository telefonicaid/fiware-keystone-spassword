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

from oslo_db.sqlalchemy import utils
import sqlalchemy as sql


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    spassword_table = utils.get_table(migrate_engine, 'spassword')

    sndfa = sql.Column('sndfa', sql.Boolean())
    sndfa_last = sql.Column('sndfa_last', sql.DateTime())
    sndfa_code = sql.Column('sndfa_code', sql.String(32))
    sndfa_time_code = sql.Column('sndfa_time_code', sql.DateTime())
    sndfa_email = sql.Column('sndfa_email', sql.Boolean())
    sndfa_email_code = sql.Column('sndfa_email_code', sql.String(32))

    spassword_table.create_column(sndfa)
    spassword_table.create_column(sndfa_last)
    spassword_table.create_column(sndfa_code)
    spassword_table.create_column(sndfa_time_code)
    spassword_table.create_column(sndfa_email)
    spassword_table.create_column(sndfa_email_code)    
    



