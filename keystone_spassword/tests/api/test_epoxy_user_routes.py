import os
import unittest
import uuid

import requests


@unittest.skipUnless(
    all(os.environ.get(key) for key in (
        'KEYSTONE_TEST_URL', 'KEYSTONE_TEST_USERNAME',
        'KEYSTONE_TEST_PASSWORD', 'KEYSTONE_TEST_DOMAIN',
    )),
    'Requires a disposable Keystone deployment and domain administrator',
)
class TestEpoxyUserRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = os.environ['KEYSTONE_TEST_URL'].rstrip('/')
        cls.domain_name = os.environ['KEYSTONE_TEST_DOMAIN']
        auth = cls.authenticate(
            os.environ['KEYSTONE_TEST_USERNAME'],
            os.environ['KEYSTONE_TEST_PASSWORD'],
            scoped=True,
        )
        auth.raise_for_status()
        cls.token = auth.headers['X-Subject-Token']
        cls.domain_id = auth.json()['token']['domain']['id']
        cls.headers = {'X-Auth-Token': cls.token}

    @classmethod
    def authenticate(cls, name, password, scoped=False):
        auth = {
            'identity': {
                'methods': ['password'],
                'password': {'user': {
                    'name': name,
                    'domain': {'name': cls.domain_name},
                    'password': password,
                }},
            },
        }
        if scoped:
            auth['scope'] = {'domain': {'name': cls.domain_name}}
        return requests.post(
            cls.url + '/auth/tokens', json={'auth': auth}, timeout=30
        )

    def create_user(self, name, password):
        response = requests.post(
            self.url + '/users', headers=self.headers,
            json={'user': {
                'name': name, 'domain_id': self.domain_id,
                'password': password,
            }},
            timeout=30,
        )
        self.assertEqual(201, response.status_code, response.text)
        user_id = response.json()['user']['id']
        self.addCleanup(self.delete_user, user_id)
        return user_id

    def delete_user(self, user_id):
        response = requests.delete(
            self.url + '/users/' + user_id, headers=self.headers, timeout=30
        )
        self.assertEqual(204, response.status_code, response.text)

    def test_collection_and_member_password_enforcement(self):
        name = 'epoxy-test-' + uuid.uuid4().hex
        password = 'S0me$tr0ngP@ssword!'
        response = requests.post(
            self.url + '/users', headers=self.headers,
            json={'user': {
                'name': name, 'domain_id': self.domain_id, 'password': '1234',
            }},
            timeout=30,
        )
        self.assertEqual(400, response.status_code, response.text)

        user_id = self.create_user(name, password)
        response = requests.get(
            self.url + '/users', headers=self.headers,
            params={'name': name}, timeout=30,
        )
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(
            [user_id], [user['id'] for user in response.json()['users']]
        )
        response = requests.get(
            self.url + '/users/' + user_id, headers=self.headers, timeout=30
        )
        self.assertEqual(200, response.status_code, response.text)
        response = requests.patch(
            self.url + '/users/' + user_id, headers=self.headers,
            json={'user': {'password': '1234'}}, timeout=30,
        )
        self.assertEqual(401, response.status_code, response.text)
        response = requests.patch(
            self.url + '/OS-SCIM/Users/' + user_id, headers=self.headers,
            json={'userName': name, 'password': '1234'}, timeout=30,
        )
        self.assertEqual(400, response.status_code, response.text)
        self.assertIn('SPASSWORD', response.text)
        response = requests.patch(
            self.url + '/users/' + user_id, headers=self.headers,
            json={'user': {'password': 'N3w$tr0ngP@ssword!'}}, timeout=30,
        )
        self.assertEqual(200, response.status_code, response.text)
        response = self.authenticate(name, 'N3w$tr0ngP@ssword!')
        self.assertEqual(201, response.status_code, response.text)
        user_headers = {'X-Auth-Token': response.headers['X-Subject-Token']}
        response = requests.post(
            self.url + '/users/' + user_id + '/password', headers=user_headers,
            json={'user': {
                'original_password': 'N3w$tr0ngP@ssword!', 'password': '1234',
            }},
            timeout=30,
        )
        self.assertEqual(400, response.status_code, response.text)
        response = requests.post(
            self.url + '/users/' + user_id + '/password', headers=user_headers,
            json={'user': {
                'original_password': 'N3w$tr0ngP@ssword!',
                'password': 'An0ther$tr0ngP@ssword!',
            }},
            timeout=30,
        )
        self.assertEqual(204, response.status_code, response.text)
        response = self.authenticate(name, 'An0ther$tr0ngP@ssword!')
        self.assertEqual(201, response.status_code, response.text)

    def test_user_cannot_update_another_users_password(self):
        password = 'S0me$tr0ngP@ssword!'
        name = 'epoxy-test-' + uuid.uuid4().hex
        self.create_user(name, password)
        target = self.create_user('epoxy-test-' + uuid.uuid4().hex, password)
        auth = self.authenticate(name, password)
        self.assertEqual(201, auth.status_code, auth.text)
        response = requests.patch(
            self.url + '/users/' + target,
            headers={'X-Auth-Token': auth.headers['X-Subject-Token']},
            json={'user': {'password': 'N3w$tr0ngP@ssword!'}}, timeout=30,
        )
        self.assertEqual(403, response.status_code, response.text)

    @unittest.skipUnless(
        os.environ.get('KEYSTONE_TEST_POLICY_SCOPE_DISABLED') == 'true',
        'Requires a deployment with scope enforcement disabled',
    )
    def test_domain_admin_can_manage_only_own_domain_roles(self):
        domain_name = 'Default'
        domain_id = 'default'
        user_name = 'flamingo-test-' + uuid.uuid4().hex
        password = 'S0me$tr0ngP@ssword!'
        response = requests.post(
            self.url + '/users', headers=self.headers,
            json={'user': {
                'name': user_name, 'domain_id': domain_id,
                'password': password,
            }},
            timeout=30,
        )
        self.assertEqual(201, response.status_code, response.text)
        user_id = response.json()['user']['id']
        self.addCleanup(self.delete_user, user_id)
        response = requests.get(
            self.url + '/roles', headers=self.headers,
            params={'name': 'admin'}, timeout=30,
        )
        self.assertEqual(200, response.status_code, response.text)
        role_id = response.json()['roles'][0]['id']
        response = requests.put(
            self.url + '/domains/' + domain_id + '/users/' + user_id
            + '/roles/' + role_id, headers=self.headers, timeout=30,
        )
        self.assertEqual(204, response.status_code, response.text)
        response = requests.post(
            self.url + '/auth/tokens', json={'auth': {
                'identity': {'methods': ['password'], 'password': {'user': {
                    'name': user_name, 'domain': {'name': domain_name},
                    'password': password,
                }}},
                'scope': {'domain': {'id': domain_id}},
            }}, timeout=30,
        )
        self.assertEqual(201, response.status_code, response.text)
        headers = {'X-Auth-Token': response.headers['X-Subject-Token']}
        response = requests.post(
            self.url + '/roles', headers=headers,
            json={'role': {'name': 'domain-role', 'domain_id': domain_id}},
            timeout=30,
        )
        self.assertEqual(201, response.status_code, response.text)
        created_role_id = response.json()['role']['id']
        self.addCleanup(
            lambda: self.assertEqual(
                204, requests.delete(
                    self.url + '/roles/' + created_role_id,
                    headers=self.headers, timeout=30,
                ).status_code,
            )
        )
        response = requests.get(
            self.url + '/roles', headers=headers,
            params={'domain_id': domain_id}, timeout=30,
        )
        self.assertEqual(200, response.status_code, response.text)
        self.assertIn(created_role_id, [r['id'] for r in response.json()['roles']])
        response = requests.post(
            self.url + '/roles', headers=headers,
            json={'role': {'name': 'foreign-role', 'domain_id': self.domain_id}},
            timeout=30,
        )
        self.assertEqual(403, response.status_code, response.text)
