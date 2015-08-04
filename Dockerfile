FROM centos:6

MAINTAINER IoT team

RUN yum update -y && yum install -y wget
RUN wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
RUN yum localinstall -y --nogpgcheck epel-release-6-8.noarch.rpm

#RUN yum -y install mysql-server mysql
#RUN service mysqld start

RUN yum -y install rpm-build
RUN yum -y install python git python-pip python-devel python-virtualenv gcc ssh

RUN yum install -y https://repos.fedorapeople.org/repos/openstack/openstack-icehouse/rdo-release-icehouse-4.noarch.rpm
RUN yum -y install openstack-utils openstack-keystone python-keystoneclient
RUN yum -y install wget unzip nc jq
RUN yum -y install cracklib cracklib-python

RUN openstack-config --set /etc/keystone/keystone.conf \
    database connection mysql://keystone:keystone@localhost/keystone

RUN openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT admin_token ADMIN

RUN openstack-config --set /etc/keystone/keystone.conf \
    DEFAULT public_port 5001

RUN openstack-config --set /etc/keystone/keystone.conf \
    os_inherit enabled true

RUN openstack-config --set /etc/keystone/keystone.conf \
    token provider keystone.token.providers.uuid.Provider

#RUN echo "CREATE DATABASE keystone; GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' \
#  IDENTIFIED BY 'keystone'; GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' \
#  IDENTIFIED BY 'keystone';" | /usr/bin/mysql -u root -h localhost

RUN keystone-manage db_sync keystone


RUN keystone-manage pki_setup --keystone-user keystone --keystone-group keystone
RUN chown -R keystone:keystone /etc/keystone/ssl
RUN chmod -R o-rwx /etc/keystone/ssl

RUN service openstack-keystone start

RUN chkconfig openstack-keystone on
