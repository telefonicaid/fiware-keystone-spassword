from keystone.common import dependency
from keystone.common import sql
from keystone import exception
from keystone.identity.mapping_backends import mapping as identity_mapping
from keystone.identity.mapping_backends.sql import Mapping
from keystone.identity.backends import sql as model
try: from oslo_log import log
except ImportError: from keystone.openstack.common import log

LOG = log.getLogger(__name__)

@dependency.requires('identity_api')
class IdGroupLdapMapping(Mapping):

    def get_public_id(self, local_entity):

        if (local_entity['entity_type'] == identity_mapping.EntityType.GROUP):
            LOG.debug('Trying to get public_id for group %s in %s' % (local_entity['local_id'],
                                                                      local_entity['domain_id']))
            try:
                session = sql.get_session()
                query = session.query(model.Group)
                query = query.filter_by(name=local_entity['local_id'])
                query = query.filter_by(domain_id=local_entity['domain_id'])
                try:
                    group_ref = query.one()
                except sql.NotFound:
                    raise exception.GroupNotFound(group_id=local_entity['local_id'])
                group = group_ref.to_dict()

                public_id = group['id']
                LOG.debug('Public_id for group %s in %s is: %s ' % (local_entity['local_id'],
                                                                    local_entity['domain_id'],
                                                                    public_id))
                return public_id
            except Exception:
                return None
        else:
            return super(Mapping, self).get_public_id(local_entity)

