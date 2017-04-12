distro = 'fedora'
pybin = '/usr/bin/python3'
script['pre'] = """#!/bin/bash
touch /root/BDISK
"""
script['post'] = """#!/bin/bash
rm -f /root/BDISK
"""
pkg['pre'] = ['yum', 'makecache']
pkg['install'] = ['yum', '-y', 'install', '%PKG%']
pkg['check'] = ['rpm', '-qi', '%PKG']
