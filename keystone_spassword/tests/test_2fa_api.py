import uuid
import json

import urllib2
import base64
import StringIO
import requests
import logging
import time


KEYSTONE_PROTOCOL = "http"
KEYSTONE_HOST = "localhost"
KEYSTONE_PORT = "5001"
TEST_SERVICE_NAME="smartcity"
TEST_SUBSERVICE_NAME1="basuras"
TEST_SUBSERVICE_NAME2="electricidad"
TEST_SERVICE_ADMIN_USER="adm1"
TEST_SERVICE_ADMIN_USER2="pepe"
TEST_SERVICE_ADMIN_PASSWORD="4pass1w0rd"


class RestOperations(object):
    '''
       IoT IdM (keystone + keypass)
    '''

    def __init__(self,
                 ENDPOINT_NAME="",
                 PROTOCOL=None,
                 HOST=None,
                 PORT=None,
                 CORRELATOR_ID=None,
                 TRANSACTION_ID=None):

        self.ENDPOINT_NAME = ENDPOINT_NAME
        self.PROTOCOL = PROTOCOL
        self.HOST = HOST
        self.PORT = PORT
        if PROTOCOL and HOST and PORT:
            self.base_url = PROTOCOL+'://'+HOST+':'+PORT
        else:
            self.base_url = None

        if TRANSACTION_ID:
            self.TRANSACTION_ID = TRANSACTION_ID
        else:
            self.TRANSACTION_ID = None

        if CORRELATOR_ID:
            self.CORRELATOR_ID = CORRELATOR_ID
        else:
            self.CORRELATOR_ID = None


    def rest_request(self, url, method, user=None, password=None,
                     data=None, json_data=True, relative_url=True,
                     auth_token=None, subject_token=None, fiware_service=None,
                     fiware_service_path=None):
        '''Does an (optionally) authorized REST request with optional JSON data.

        In case of HTTP error, the exception is returned normally instead of
        raised and, if JSON error data is present in the response, .msg will
        contain the error detail.'''
        service_start = time.time()
        user = user or None
        password = password or None

        if relative_url:
            # Create real url
            url = self.base_url + url

        if data:
            if json_data:
                request = urllib2.Request(
                    url, data=json.dumps(data))
            else:
                request = urllib2.Request(url, data=data)
        else:
            request = urllib2.Request(url)
        request.get_method = lambda: method

        if json_data:
            request.add_header('Accept', 'application/json')
            if data:
                request.add_header('Content-Type', 'application/json')
        else:
            request.add_header('Accept', 'application/xml')
            if data:
                request.add_header('Content-Type', 'application/xml')

        if user and password:
            base64string = base64.encodestring(
                '%s:%s' % (user, password))[:-1]
            authheader = "Basic %s" % base64string
            request.add_header("Authorization", authheader)

        if auth_token:
            request.add_header('X-Auth-Token', auth_token)

        if subject_token:
            request.add_header('X-Subject-Token', subject_token)

        if fiware_service:
            request.add_header('Fiware-Service', fiware_service)

        if fiware_service_path:
            request.add_header('Fiware-ServicePath', fiware_service_path)

        if self.TRANSACTION_ID:
            request.add_header('Fiware-Transaction', self.TRANSACTION_ID)

        if self.CORRELATOR_ID:
            request.add_header('Fiware-Correlator', self.CORRELATOR_ID)

        res = None

        try:
            res = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            res = e
            data = res.read()
            try:
                data_json = json.loads(data)
                res.raw_json = data_json
                if data_json and isinstance(data_json, dict) and \
                    'detail' in data_json:
                    res.msg = data_json['detail']
                if data_json and isinstance(data_json, dict) and \
                    'error' in data_json:
                    if data_json['error'] and \
                        isinstance(data_json['error'], dict) and \
                        'message' in data_json['error']:
                        res.msg = data_json['error']['message']
                if data_json and isinstance(data_json, dict) and \
                    'message' in data_json:
                    res.msg = data_json['message']

            except ValueError:
                res.msg = data
            except Exception, e:
                print e
        except urllib2.URLError, e:
            data = None
            res = e
            res.code = 500
            res.msg = self.ENDPOINT_NAME + " endpoint ERROR: " + res.args[0][1]

        return res


class TestRestOperations(RestOperations):

    def __init__(self, PROTOCOL, HOST, PORT):
        RestOperations.__init__(self,
                                "KEYSTONE",
                                PROTOCOL,
                                HOST,
                                PORT)
        self.keystone_endpoint_url = PROTOCOL + '://' + HOST + ":" + PORT

    def getToken(self, data, SCOPED=True):
        auth_data = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": data["SERVICE_ADMIN_USER"],
                            "password": data["SERVICE_ADMIN_PASSWORD"]
                        }
                    }
                }
            }
        }
        if "SERVICE_NAME" in data:
            auth_data['auth']['identity']['password']['user'].update(
                {"domain": {"name": data["SERVICE_NAME"]}})

            if SCOPED:
                scope_domain = {
                "scope": {
                    "domain": {
                        "name": data["SERVICE_NAME"]
                    }
                }
                }
                auth_data['auth'].update(scope_domain)

        res = self.rest_request(
            url=self.keystone_endpoint_url + '/v3/auth/tokens',
            relative_url=False,
            method='POST', data=auth_data)
        assert res.code == 201, (res.code, res.msg)
        return res

    def getScopedToken(self, data):
        auth_data = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": data["SERVICE_ADMIN_USER"],
                            "password": data["SERVICE_ADMIN_PASSWORD"]
                        }
                    }
                }
            }
        }
        if "SERVICE_NAME" in data and "SUBSERVICE_NAME" in data:
            auth_data['auth']['identity']['password']['user'].update(
                {"domain": {"name": data["SERVICE_NAME"]}})

            scope_domain = {
                "scope": {
                    "project": {
                        "domain": {
                            "name": data["SERVICE_NAME"]
                        },
                        "name": "/" + data["SUBSERVICE_NAME"]
                    }
                }
            }
            auth_data['auth'].update(scope_domain)
        res = self.rest_request(
            url=self.keystone_endpoint_url + '/v3/auth/tokens',
            relative_url=False,
            method='POST', data=auth_data)
        assert res.code == 201, (res.code, res.msg)
        return res

    def getUserId(self, data):
        token_res = self.getToken(data)
        data_response = token_res.read()
        json_body_response = json.loads(data_response)
        return json_body_response['token']['user']['id']


class Test_2fa_RestView(object):

    def __init__(self):
        self.suffix = str(uuid.uuid4())[:8]

        self.payload_data_ok = {
            "SERVICE_NAME": TEST_SERVICE_NAME,
            "SERVICE_ADMIN_USER": TEST_SERVICE_ADMIN_USER,
            "SERVICE_ADMIN_PASSWORD": TEST_SERVICE_ADMIN_PASSWORD,
        }
        self.payload_data2_ok = {
            "SERVICE_NAME": TEST_SERVICE_NAME,
            "SERVICE_ADMIN_USER": TEST_SERVICE_ADMIN_USER2,
            "SERVICE_ADMIN_PASSWORD": TEST_SERVICE_ADMIN_PASSWORD,
        }
        self.payload_data3_ok = {
            "enable": True
        }
        self.TestRestOps = TestRestOperations(PROTOCOL=KEYSTONE_PROTOCOL,
                                              HOST=KEYSTONE_HOST,
                                              PORT=KEYSTONE_PORT)

    def test_checkemail_ok(self):
        token_res = self.TestRestOps.getToken(self.payload_data_ok)
        auth_token = token_res.headers.get('X-Subject-Token')
        user_id = self.TestRestOps.getUserId(self.payload_data_ok)
        res = self.TestRestOps.rest_request(
            method="GET",
            url="/v3/users/" + user_id + "/checkemail",
            auth_token=auth_token,
            json_data=False,
            data=None)
        assert res.code == 200, (res.code, res.msg, res.raw_json)

        code = "badcode"
        res = self.TestRestOps.rest_request(
            method="GET",
            url="/v3/users/" + user_id + "/checkemail/" + code,
            auth_token=auth_token,
            json_data=False,
            data=None)
        assert res.code == 401, (res.code, res.msg, res.raw_json)


    def test_sndfa_ok(self):
        token_res = self.TestRestOps.getToken(self.payload_data2_ok)
        auth_token = token_res.headers.get('X-Subject-Token')
        user_id = self.TestRestOps.getUserId(self.payload_data2_ok)
        res = self.TestRestOps.rest_request(
            method="POST",
            url="/v3/users/" + user_id + "/sndfa",
            auth_token=auth_token,
            json_data=True,
            data=self.payload_data3_ok)
        assert res.code == 200, (res.code, res.msg, res.raw_json)

        code = "badcode"
        res = self.TestRestOps.rest_request(
            method="GET",
            url="/v3/users/" + user_id + "/sndfa/" + code,
            auth_token=auth_token,
            json_data=False,
            data=None)
        assert res.code == 401, (res.code, res.msg, res.raw_json)

    def test_recover_nok(self):
        token_res = self.TestRestOps.getToken(self.payload_data_ok)
        auth_token = token_res.headers.get('X-Subject-Token')
        user_id = self.TestRestOps.getUserId(self.payload_data_ok)
        res = self.TestRestOps.rest_request(
            method="GET",
            url="/v3/users/" + user_id + "/recover_password",
            auth_token=auth_token,
            json_data=False,
            data=None)
        # User with email not checked
        assert res.code == 401, (res.code, res.msg, res.raw_json)

if __name__ == '__main__':

    # Tests
    test_2fa = Test_2fa_RestView()
    test_2fa.test_checkemail_ok()
    test_2fa.test_sndfa_ok()
    test_2fa.test_recover_nok()
