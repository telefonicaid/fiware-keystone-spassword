# Keystone SPASSWORD extension

[![FIWARE Security](https://nexus.lab.fiware.org/static/badges/chapters/security.svg)](https://www.fiware.org/developers/catalogue/)
[![License: Apache 2.0](https://img.shields.io/github/license/telefonicaid/fiware-keypass.svg)](https://opensource.org/licenses/Apache-2.0)
<br/>
![Status](https://nexus.lab.fiware.org/static/badges/statuses/incubating.svg)

Keystone SPASSWORD is an OpenStack Keystone extension that enables
some extra security checks over user passwords, as force the usage of strong passwords,
expiration time for a password, number of bad login attempts before user account became temporarily blocked,
a recover procedure password, a second factor authentication (2FA)  and so on.


## Keystone versions
- 1.4.X uses keystone Liberty
- 1.5.X uses keystne Mitaka
- 1.6.0 uses keystone Newton
- 1.7.0 uses keystone Pike
- 1.8.0 uses keystone Queens
- 1.9.0 uses keystone Rocky
- 1.10.0 and further uses keystone Stein


## Installing and Configuration

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
* `enabled` is a boolean which enables (true) or disables (false) if Keystone Spassword plugin feature is available in Keystone instance.
* `pwd_exp_days` indicates the time in days in which user password will be expired if user password is not changed before.
* `pwd_max_tries` indicate max number of bad login tries before user ccount is blocked (no login/token request is allowed)
* `pwd_block_minutes` indicate the time in minutes in whcih and user account would be blocked.
* `pwd_user_blacklist` list of user ids separated by `,` excluded by spassword.

keystone-spassword enables two new authentication and identity plugins, which extends
default provided plugins to ensure the use of strong passwords, to check expiration time
and to control the number of tries that an user can use badly their password before be blocked.
This way keystone-spassword extend token data returned from keystone to user by
"POST /v3/auth/tokens", including new fields in 'extra' dictionary of 'token':

```
 "extras": {
     "password_creation_time": "2016-12-01T08:55:34Z",
     "pwd_user_in_blacklist": false,
     "password_expiration_time": "2017-12-01T08:55:34Z",
     "last_login_attempt_time": "2017-05-01T06:45:00Z"
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
For more details see [RPM spec steps ][./keystone-spassword.spec).


### Install Keystone

There is a complete guide to install step by step keystone for development purposes:

https://github.com/telefonicaid/fiware-pep-steelskin/blob/master/keystoneInstallation.md


### Docker Installation
Thre is a docker container image which includes keystone + keystone scim plugin + keystone spassword plugin:
https://hub.docker.com/repository/docker/telefonicaiot/fiware-keystone-spassword

There are some [env vars  for configuration](docs/DOCKER.md)

#### Upgrade from a older version:
How to upgrade to latest (1.10.0) docker release:

Normal procedure is stop container, update version in docker-compose and then up container; then container will be recreated.
But, if starting version is between 1.4.X and 1.6.X then some steps should be done to achieve that.

##### Upgrade from 1.4.X
-> needs be upgrade to 1.5.4 version before and then perform the steps described for that version.
In this step is important to use and SQL schema created by Keystone, not just recover from the scratch a sql dump backup, since and sql dump backup has not all required data to migration 1.4.x to 1.5.x will be successfully executed. More info about this issue is found at https://github.com/telefonicaid/fiware-keystone-spassword/issues/194


##### Upgrade from 1.5.X or 1.6.0
-> needs a workaround:
Before update image in docker-compose the following commands should be executed:

Backup `keystone.spassword` table
```
mysqldump -u root -p keystone spassword > table_spassword.sql
```
Exec the following commands
```
mysql -h iot-mysql -u root -p
use keystone;
drop table spassword;
delete from migrate_version where repository_id='keystone_spassword';
```
Then stop container and update image in docker-compose and up again container; then container will be recreated.

Recover keystone.spassword table using backup.
```
mysql -u root -p keystone < table_spassword.sql
```
Restart again keystone container

##### Upgrade from 1.7.0,  1.8.0, 1.9.0 
-> no workaround needed


## Usage

SPASSWORD extension reuses the authentication and authorization mechanisms provided
by Keystone. This document assumes that the reader has previous experience
with Keystone, but as a reference you can read more about the Keystone
Authentication and Authorization mechanism in it's
[official documentation](https://github.com/openstack/identity-api/blob/master/v3/src/markdown/identity-api-v3.md).


Moreover keystone-spassword adds a new API to retrieve all project roles for a user (aka Grants):
        
**GET '/v3/users/{user_id}/project_roles'**

This call uses a x-auth-token associated to <user_id> user.

```
[
    {
        "domain": "8960989b51164eaeaa42200ecc79a47a",
        "project_name": "/smartcity/gardens",
        "project": "031149af6c5147a782e9cf4c56e1fe11",
        "role_name": "8960989b51164eaeaa42200ecc79a47a#SubServiceAdmin",
        "role": "e0da2d91e8154a32980ed4c5a717fd91",
        "user": "bace4fd6bd9b49fda5727eb83a714a3c",
        "user_name": "user1"
    },
  ....
]
```

## Building and packaging

In any OS (Linux, OSX) with a sane build environment (basically with `rpmbuild`
installed), the RPM package can be built invoking the following command:

```
sh ./package-keystone-spassword.sh
```

## Fernet keys and HA

Since version 1.10 keystone-spassword is based on Keystone Stein and therefore uses Fernet keys. Full detail about these token could be found at [this faq](https://docs.openstack.org/keystone/stein/admin/fernet-token-faq.html).

Sumarizing the implications for HA enviroment we can say:
- Fernet keys are stored in /etc/keystone/fernet-keys folder
- Fernet keys should periodically rotated
- Fernet keys should be the same for all nodes of an HA environment.

To achieve that there are some options:
- Use a volumen for fernet keys folder content in docker based deployments.
- Distribute fernet keys folder content with a `rsync` command abroad all keystone nodes
- Ensure keystone Load Balancer is using sticky sessions [example for ha proxy](https://thisinterestsme.com/haproxy-sticky-sessions)

For non production environments there is another option: disable fernet keys rotation (i.e. by setting env var `ROTATE_FERNET_KEYS=False` in spassword 1.12.0+)

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

(until spassword 1.9.0)

```sh
keystone-manage db_sync --extension spassword
```

(from spassword 1.10.0)

```sh
keystone-manage db_sync
```

Launch server

```sh
PYTHONPATH=.:$PYTHONPATH keystone-all --config-dir etc
```


## [LDAP integration](docs/iotp_ldap.md)

## [Second Factor Authentication](docs/second_factor_auth.md)

## [Docker env vars](docs/DOCKER.md)
