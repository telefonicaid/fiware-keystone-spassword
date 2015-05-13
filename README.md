# Keystone SPASSWORD extension
Keystone SPASSWORD is an OpenStack Keystone extension that enables
some extra security checks over user passwords, as force strong passwords,
a recover procedure and so on.


## Installing

### RPM installing on RDO Openstack

Installing from RPM is pretty straightforward:

```sh
rpm -Uvh keystone-spassword-*.noarch.rpm
```

Once installed you can fine-tune options (out-of-the box the
installation configures default values for that options.

```
[spassword]
enabled=true
smtp_server = 'correo.tid.es'
smtp_port = 587
smtp_tls = True
smtp_user = 'iot_support@tid.es'
smtp_password = ''
smtp_from = "iot_support@tid.es"
password_expiration_days = 2*365/12
```

Restart Keystone server:

```
sudo service openstack-keystone restart
```

### TGZ installaton

**TBD**

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





