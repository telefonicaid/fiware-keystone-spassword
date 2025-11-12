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

import json
import unittest
import time
import base64
import requests
import logging
import urllib.request as urllib2
import urllib.error

from unittest.mock import patch, MagicMock


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
        except urllib2.URLError as e:
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
            except Exception as e:
                print(e)

        except urllib2.URLError as e:
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



class FakeResponse:
    """Simulates and object returned by urllib.request.urlopen"""
    def __init__(self, code=200, data=None, headers=None):
        self.code = code
        self.data = data or {}
        self.raw_json = data
        self.msg = ""
        self.headers = headers or {}

    def read(self):
        return json.dumps(self.data).encode("utf-8")


class TestRestOperationsMock(unittest.TestCase):

    def setUp(self):
        self.testops = TestRestOperations(
            PROTOCOL="http",
            HOST="localhost",
            PORT="5001",
        )

        self.payload = {
            "SERVICE_NAME": "smartgondor",
            "SERVICE_ADMIN_USER": "foo",
            "SERVICE_ADMIN_PASSWORD": "pwd",
        }

    @patch("urllib.request.urlopen")
    def test_get_token_ok(self, mock_urlopen):
        """It should return 201 when not valid token"""
        mock_urlopen.return_value = FakeResponse(
            code=201,
            data={"token": {"user": {"id": "fake-user-id"}}},
            headers={"X-Subject-Token": "token123"}
        )

        response = self.testops.getToken(self.payload)

        self.assertEqual(response.code, 201)
        self.assertEqual(response.headers["X-Subject-Token"], "token123")

    @patch("urllib.request.urlopen")
    def test_rest_checkemail_401(self, mock_urlopen):
        """It should return 401 when check email is wrong"""
        mock_urlopen.return_value = FakeResponse(
            code=401,
            data={"message": "Unauthorized"}
        )

        response = self.testops.rest_request(
            method="GET",
            url="/v3/users/fake/checkemail/badcode",
            auth_token="token123",
            json_data=False,
        )

        self.assertEqual(response.code, 401)


if __name__ == "__main__":
    unittest.main()
