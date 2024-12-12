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

from alembic import op
import sqlalchemy as sql

# revision identifiers, used by Alembic.
revision = '1'
down_revision = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    
    op.create_table(
        'spassword',
        sql.Column('user_id', sql.String(64), primary_key=True),
        sql.Column('user_name', sql.String(255)),
        sql.Column('domain_id', sql.String(64)),
        sql.Column('creation_time', sql.DateTime()),
        sql.Column('login_attempts', sql.Integer),
        sql.Column('last_login_attempt_time', sql.DateTime()),
        sql.Column('extra', sql.Text()),
        sql.Column('sndfa', sql.Boolean(), default=False),
        sql.Column('sndfa_last', sql.DateTime(), default=None),
        sql.Column('sndfa_code', sql.String(32), default=None),
        sql.Column('sndfa_time_code', sql.DateTime(), default=None),
        sql.Column('sndfa_email', sql.Boolean(), default=False),
        sql.Column('sndfa_email_code', sql.String(32), default=None),
        mysql_engine='InnoDB',
        mysql_charset='utf8',
    )



