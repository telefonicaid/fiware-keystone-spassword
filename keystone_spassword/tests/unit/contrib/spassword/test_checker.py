#
# Copyright 2014 Telefonica Investigacion y Desarrollo, S.A.U
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

"""Unit tests for SPASSWORD checker."""

import unittest
from unittest import mock

from keystone import exception
from keystone_spassword.contrib.spassword import checker


class TestPasswordChecker(unittest.TestCase):
    def setUp(self):
        # Crear instancia de CheckPassword
        self.pwd_checker = checker.CheckPassword()

        # Parchear CONF.spassword.enabled a True
        patcher = mock.patch('keystone_spassword.contrib.spassword.checker.CONF.spassword.enabled', True)
        self.addCleanup(patcher.stop)
        self.mock_enabled = patcher.start()

    def test_strong_password_failure(self):
        """Test that a weak password raises ValidationError."""
        # Un password débil que cracklib rechazará
        weak_password = "1234"

        self.assertRaises(
            exception.ValidationError,
            self.pwd_checker.strong_check_password,
            weak_password
        )

    def test_strong_password_success(self):
        """Test that a strong password does not raise an exception."""
        strong_password = "S0me$tr0ngP@ssword!"

        # No debería lanzar excepción
        try:
            self.pwd_checker.strong_check_password(strong_password)
        except exception.ValidationError:
            self.fail("strong_check_password() raised ValidationError unexpectedly!")


if __name__ == "__main__":
    unittest.main()
