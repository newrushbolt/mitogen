#!/usr/bin/env python

"""
Build the Docker images used for testing.
"""

import commands
import os
import shlex
import subprocess
import tempfile


DEBIAN_DOCKERFILE = r"""
FROM debian:stable
RUN apt-get update
RUN \
    apt-get install -y python2.7 openssh-server sudo rsync git strace && \
    apt-get clean
"""

CENTOS_DOCKERFILE = r"""
FROM centos:7
RUN yum clean all && \
    yum -y install -y python2.7 openssh-server sudo rsync git strace sudo && \
    yum clean all && \
    groupadd sudo && \
    ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key

"""

DOCKERFILE = r"""
COPY data/001-mitogen.sudo /etc/sudoers.d/001-mitogen
RUN \
    mkdir -p /var/run/sshd && \
    echo i-am-mitogen-test-docker-image > /etc/sentinel && \
    groupadd mitogen__sudo_nopw && \
    useradd -s /bin/bash -m mitogen__has_sudo -G SUDO_GROUP && \
    useradd -s /bin/bash -m mitogen__has_sudo_pubkey -G SUDO_GROUP && \
    useradd -s /bin/bash -m mitogen__has_sudo_nopw -G mitogen__sudo_nopw && \
    useradd -s /bin/bash -m mitogen__webapp && \
    useradd -s /bin/bash -m mitogen__pw_required && \
    useradd -s /bin/bash -m mitogen__require_tty && \
    useradd -s /bin/bash -m mitogen__require_tty_pw_required && \
    { for i in `seq 1 21`; do useradd -s /bin/bash -m mitogen__user$i; done; } && \
    ( echo 'root:rootpassword' | chpasswd; ) && \
    ( echo 'mitogen__has_sudo:has_sudo_password' | chpasswd; ) && \
    ( echo 'mitogen__has_sudo_pubkey:has_sudo_pubkey_password' | chpasswd; ) && \
    ( echo 'mitogen__has_sudo_nopw:has_sudo_nopw_password' | chpasswd; ) && \
    ( echo 'mitogen__webapp:webapp_password' | chpasswd; ) && \
    ( echo 'mitogen__pw_required:pw_required_password' | chpasswd; ) && \
    ( echo 'mitogen__require_tty:require_tty_password' | chpasswd; ) && \
    ( echo 'mitogen__require_tty_pw_required:require_tty_pw_required_password' | chpasswd; ) && \
    mkdir ~mitogen__has_sudo_pubkey/.ssh && \
    { echo '#!/bin/bash\nexec strace -ff -o /tmp/pywrap$$.trace python2.7 "$@"' > /usr/local/bin/pywrap; chmod +x /usr/local/bin/pywrap; }

COPY data/docker/mitogen__has_sudo_pubkey.key.pub /home/mitogen__has_sudo_pubkey/.ssh/authorized_keys
RUN \
    chown -R mitogen__has_sudo_pubkey ~mitogen__has_sudo_pubkey && \
    chmod -R go= ~mitogen__has_sudo_pubkey

RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
"""


def sh(s, *args):
    if args:
        s %= tuple(map(commands.mkarg, args))
    return shlex.split(s)


for (distro, wheel, prefix) in (('debian', 'sudo', DEBIAN_DOCKERFILE),
                                ('centos', 'wheel', CENTOS_DOCKERFILE)):
    mydir = os.path.abspath(os.path.dirname(__file__))
    with tempfile.NamedTemporaryFile(dir=mydir) as dockerfile_fp:
        dockerfile_fp.write(prefix)
        dockerfile_fp.write(DOCKERFILE.replace('SUDO_GROUP', wheel))
        dockerfile_fp.flush()

        subprocess.check_call(sh('docker build %s -t %s -f %s',
            mydir,
            'd2mw/mitogen-%s-test' % (distro,),
            dockerfile_fp.name
        ))
