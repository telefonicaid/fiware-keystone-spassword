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

import datetime
from unittest.mock import MagicMock, patch

import pytest

from keystone_spassword.contrib.spassword.backends.sql import (
    normalize_db_date, SPasswordModel, SPasswordUnauthorized,
    SPassword, get_spassword_session
)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_session(mocker):
    """Session mock for SQLAlchemy."""
    session = MagicMock()
    mocker.patch("backend.sql.sql.get_session", return_value=session)
    mocker.patch("backend.sql.sql.session_for_read")
    return session


@pytest.fixture
def mock_user():
    """User demo retrieved by keystone"""
    return {
        "id": "user123",
        "name": "demo",
        "domain_id": "default"
    }


# ------------------------------------------------------------------------------
# Tests: normalize_db_date
# ------------------------------------------------------------------------------

def test_normalize_db_date_remove_timezone():
    dt = datetime.datetime.now(datetime.timezone.utc)
    result = normalize_db_date(dt)
    assert result.tzinfo is None


def test_normalize_db_date_keep_naive():
    dt = datetime.datetime.now()
    result = normalize_db_date(dt)
    assert result is dt


# ------------------------------------------------------------------------------
# Tests: SPasswordModel
# ------------------------------------------------------------------------------

def test_spassword_model_defaults():
    model = SPasswordModel(
        user_id="user123",
        user_name="demo",
        domain_id="default"
    )
    assert model.login_attempts == 0
    assert model.sndfa is False
    assert model.sndfa_email is False


# ------------------------------------------------------------------------------
# Tests: SPassword.set_user_creation_time
# ------------------------------------------------------------------------------

def test_set_user_creation_time_creates_entry(mock_session, mock_user, mocker):
    mocker.patch("backend.sql.get_spassword_session", return_value=(None, mock_session))

    sp = SPassword()
    result = sp.set_user_creation_time(mock_user)

    assert result["user_id"] == "user123"
    assert mock_session.add.called


def test_set_user_creation_time_existing_user(mock_session, mock_user, mocker):
    existing = SPasswordModel.from_dict({
        "user_id": "user123",
        "user_name": "demo",
        "domain_id": "default",
        "creation_time": datetime.datetime.utcnow(),
        "sndfa": False,
    })

    mocker.patch("backend.sql.get_spassword_session", return_value=(existing, mock_session))

    sp = SPassword()
    result = sp.set_user_creation_time(mock_user)

    # it should reset login_attempts to 0
    assert result["login_attempts"] == 0
    assert mock_session.add.called


# ------------------------------------------------------------------------------
# Tests: modify_black / get_black
# ------------------------------------------------------------------------------

def test_modify_black_and_get_black(mock_session, mock_user, mocker):
    model = SPasswordModel.from_dict({
        "user_id": "user123",
        "user_name": "demo",
        "domain_id": "default",
        "creation_time": datetime.datetime.utcnow(),
    })

    mocker.patch("backend.sql.get_spassword_session", return_value=(model, mock_session))

    sp = SPassword()

    assert sp.modify_black("user123", True)
    assert model.extra == {"black": "True"}

    assert sp.get_black("user123") is True


# ------------------------------------------------------------------------------
# Tests: 2FA - set_user_sndfa_code
# ------------------------------------------------------------------------------

def test_set_user_sndfa_code(mock_session, mocker, mock_user):
    model = SPasswordModel.from_dict({
        "user_id": "user123",
        "user_name": "demo",
        "domain_id": "default",
        "sndfa": True,
        "sndfa_email": True,
    })

    mocker.patch("backend.sql.get_spassword_session", return_value=(model, mock_session))

    sp = SPassword()
    sp.set_user_sndfa_code(mock_user, "123456")

    assert model.sndfa_code == "123456"
    assert mock_session.add.called


# ------------------------------------------------------------------------------
# Tests: check_sndfa_code
# ------------------------------------------------------------------------------

def test_check_sndfa_code_ok(mock_session, mocker):
    model = SPasswordModel.from_dict({
        "user_id": "user123",
        "sndfa": True,
        "sndfa_email": True,
        "sndfa_code": "123456"
    })

    mocker.patch("backend.sql.get_spassword_session", return_value=(model, mock_session))
    sp = SPassword()

    assert sp.check_sndfa_code("user123", "123456") is True


def test_check_sndfa_code_wrong(mock_session, mocker):
    model = SPasswordModel.from_dict({
        "user_id": "user123",
        "sndfa": True,
        "sndfa_email": True,
        "sndfa_code": "123456"
    })

    mocker.patch("backend.sql.get_spassword_session", return_value=(model, mock_session))
    sp = SPassword()

    assert sp.check_sndfa_code("user123", "999999") is False
