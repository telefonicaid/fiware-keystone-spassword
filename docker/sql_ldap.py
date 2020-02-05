# Copyright 2014 IBM Corp.
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


# This file is the sql_ldap mapping id driver for Liberty or uppper versions of Keystone

from keystone.common import dependency
from keystone.common import sql
from keystone import identity
from keystone import exception
from keystone.identity.mapping_backends import mapping as identity_mapping
from keystone.identity.backends import sql as model
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

LOG = log.getLogger(__name__)

class IDMapping(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'id_mapping'
    public_id = sql.Column(sql.String(64), primary_key=True)
    domain_id = sql.Column(sql.String(64), nullable=False)
    local_id = sql.Column(sql.String(64), nullable=False)
    # NOTE(henry-nash); Postgres requires a name to be defined for an Enum
    entity_type = sql.Column(
        sql.Enum(identity_mapping.EntityType.USER,
                 identity_mapping.EntityType.GROUP,
                 name='entity_type'),
        nullable=False)
    # Unique constraint to ensure you can't store more than one mapping to the
    # same underlying values
    __table_args__ = (
        sql.UniqueConstraint('domain_id', 'local_id', 'entity_type'), {})


@dependency.requires('id_generator_api')
class Mapping(identity.MappingDriverV8):

    def get_session(self):
        try:
            session = sql.get_session()
        except Exception:
            with sql.session_for_write() as session:
                None
        return session

    def get_public_id(self, local_entity):
        if (local_entity['entity_type'] == identity_mapping.EntityType.GROUP):
            LOG.debug('Trying to get public_id for group %s in %s' % (local_entity['local_id'],
                                                                      local_entity['domain_id']))
            try:
                session = self.get_session()
                query = session.query(model.Group)
                query = query.filter_by(name=local_entity['local_id'])
                query = query.filter_by(domain_id=local_entity['domain_id'])
                try:
                    group_ref = query.one()
                except sql.NotFound:
                    session = self.get_session()
                    query = session.query(IDMapping.public_id)
                    query = query.filter_by(domain_id=local_entity['domain_id'])
                    query = query.filter_by(local_id=local_entity['local_id'])
                    query = query.filter_by(entity_type=local_entity['entity_type'])
                    try:
                        public_ref = query.one()
                        public_id = public_ref.public_id
                        return public_id
                    except sql.NotFound:
                        return None

                group = group_ref.to_dict()
                public_id = group['id']
                LOG.debug('Public_id for group %s in %s is: %s ' % (local_entity['local_id'],
                                                                    local_entity['domain_id'],
                                                                    public_id))
                return public_id
            except Exception:
                return None
        else:        
            # NOTE(henry-nash): Since the Public ID is regeneratable, rather
            # than search for the entry using the local entity values, we
            # could create the hash and do a PK lookup.  However this would only
            # work if we hashed all the entries, even those that already generate
            # UUIDs, like SQL.  Further, this would only work if the generation
            # algorithm was immutable (e.g. it had always been sha256).
            session = self.get_session()
            query = session.query(IDMapping.public_id)
            query = query.filter_by(domain_id=local_entity['domain_id'])
            query = query.filter_by(local_id=local_entity['local_id'])
            query = query.filter_by(entity_type=local_entity['entity_type'])
            try:
                public_ref = query.one()
                public_id = public_ref.public_id
                return public_id
            except sql.NotFound:
                return None

    def get_id_mapping(self, public_id):
        session = self.get_session()
        mapping_ref = session.query(IDMapping).get(public_id)
        if mapping_ref:
            return mapping_ref.to_dict()

    def create_id_mapping(self, local_entity, public_id=None):
        entity = local_entity.copy()
        with sql.session_for_write() as session:
            if public_id is None:
                public_id = self.id_generator_api.generate_public_ID(entity)
            entity['public_id'] = public_id
            mapping_ref = IDMapping.from_dict(entity)
            session.add(mapping_ref)
        return public_id

    def delete_id_mapping(self, public_id):
        with sql.session_for_write() as session:
            try:
                session.query(IDMapping).filter(
                    IDMapping.public_id == public_id).delete()
            except sql.NotFound:
                # NOTE(morganfainberg): There is nothing to delete and nothing
                # to do.
                pass

    def purge_mappings(self, purge_filter):
        session = self.get_session()
        query = session.query(IDMapping)
        if 'domain_id' in purge_filter:
            query = query.filter_by(domain_id=purge_filter['domain_id'])
        if 'public_id' in purge_filter:
            query = query.filter_by(public_id=purge_filter['public_id'])
        if 'local_id' in purge_filter:
            query = query.filter_by(local_id=purge_filter['local_id'])
        if 'entity_type' in purge_filter:
            query = query.filter_by(entity_type=purge_filter['entity_type'])
        query.delete()
