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

from keystone import exception

class CheckPassword(object):

    def strong_check_password(self, new_password):
        # Check password strengh
        try:
            import cracklib
            try:
                cracklib.VeryFascistCheck(new_password)
            except ValueError, msg:
                raise exception.ValidationError(
                    target='user',
                    attribute='The password is too weak ({0})'.format(msg))
        except ImportError:  # not used if not configured (dev environments)
            LOG.error('cracklib module is not properly configured, '
                        'weak password can be used when changing')
