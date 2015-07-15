FROM centos:6

MAINTAINER IoT team

RUN yum update -y && yum install -y wget
RUN wget http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
RUN yum localinstall -y --nogpgcheck epel-release-6-8.noarch.rpm

RUN yum -y install rpm-build
RUN yum -y install python git python-pip python-devel python-virtualenv gcc ssh
RUN yum install -y openstack-utils openstack-keystone python-keystoneclient
RUN yum install -y wget unzip nc jq 
RUN yum install -y cracklib cracklib-python

RUN sudo yum -y install mysql-server mysql
RUN sudo service mysqld start
