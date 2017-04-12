distro = 'debian'
pybin = '/usr/bin/python'
guestenv['DEBIAN_FRONTEND'] = 'noninteractive'
script['pre'] = """#!/bin/bash
touch /root/BDISK
"""
script['post'] = """#!/bin/bash
rm -f /root/BDISK
"""
pkg['pre'] = ['apt-get', '-q', '-y', 'update']
pkg['install'] = ['apt-get', '-q', '-y', '-o Dpkg::Options::="--force-confdef"', '-o Dpkg::Options::="--force-confold"', 'install', '%PKG%']
pkg['check'] = ['dpkg-query', '-f', "'${binary:Package}\n'", '-W', '%PKG']
