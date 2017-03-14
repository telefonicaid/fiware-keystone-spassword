# Keystone SPASSWORD extension
Keystone SPASSWORD is an OpenStack Keystone extension that enables
some extra security checks over user passwords, as force the usage of strong passwords,
expiration time for a password, number of bad login attempts before user account became temporarily blocked,
a recover procedure password and so on.


## Installing

### RPM installing on RDO Openstack

Installing from RPM is pretty straightforward:

```sh
rpm -Uvh keystone-spassword-*.noarch.rpm
```

Once installed you can fine-tune options (out-of-the box the
installation configures default values for that options at /etc/keystone/keystone.conf).


```
[spassword]
enabled = true
pwd_exp_days = 365
pwd_max_tries = 5
pwd_block_minutes = 30
pwd_user_blacklist = user_id_list
smtp_server = '0.0.0.0'
smtp_port = 587
smtp_tls = true
smtp_user = 'smtpuser@yourdomain.com'
smtp_password = 'yourpassword'
smtp_from = 'smtpuser'
```

keystone-spassword enables two new authentication and identity plugins, which extends
default provided plugins to ensure the use of strong passwords, to check expiration time
and to control the number of tries that an user can use badly their password before be blocked.
This way keystone-spassword extend token data returned from keystone to user by
"POST /v3/auth/tokens", including new fields in 'extra' dictionary of 'token':

```
 "extras": {
     "password_creation_time": "2016-12-01T08:55:34Z",
     "pwd_user_in_blacklist": false,
     "password_expiration_time": "2017-12-01T08:55:34Z"
     },
```


```
[auth]
password=keystone_spassword.contrib.spassword.SPassword
```
and
```
[identity]
driver=keystone_spassword.contrib.spassword.backends.sql.Identity
```

```
[filter:spassword_checker]
paste.filter_factory = keystone_spassword.contrib.spassword.routers:PasswordExtension.factory

[filter:spassword_time]
paste.filter_factory = keystone_spassword.contrib.spassword:PasswordMiddleware.factory
```


Restart Keystone server:

```
sudo service openstack-keystone restart
```

### TGZ installaton

Uncompress tgz file plugin into python site-packages directory.
Make a soft link from keystone contrib directory to that directory.
For deep details follow [RPM spec steps ][./keystone-spassword.spec).


### Install Keystone

There is a complete guide to install step by step keystone:

https://github.com/telefonicaid/fiware-pep-steelskin/blob/master/keystoneInstallation.md

## Usage

SPASSWORD extension reuses the authentication and authorization mechanisms provided
by Keystone. This document assumes that the reader has previous experience
with Keystone, but as a reference you can read more about the Keystone
Authentication and Authorization mechanism in it's
[official documentation](https://github.com/openstack/identity-api/blob/master/v3/src/markdown/identity-api-v3.md).


## Building and packaging

In any OS (Linux, OSX) with a sane build environment (basically with `rpmbuild`
installed), the RPM package can be built invoking the following command:

```
sh ./package-keystone-spassword.sh
```

## Hacking

Local development (by default using `sqlite`). Running a local development
server is useful to test a full featured Keystone server with SPASSWORD extension,
and installation is straightforward following these steps:

Setup a virtualenv (highly recommended).

```sh
virtualenv .venv
```

Activate virtualenv

```sh
source .venv/bin/activate
```

Download dependencies

```sh
pip install -r requirements.txt
pip install -r test-requirements.txt
pip install tox
```

Running tests (functional and unit tests)

```sh
tox -e py27
```

Setting up local development server. First populate database (remember that
this will use `sqlite`).

```sh
keystone-manage db_sync --extension spassword
```

Launch server

```sh
PYTHONPATH=.:$PYTHONPATH keystone-all --config-dir etc
```


## [LDAP integration](docs/iotp_ldap.md)


