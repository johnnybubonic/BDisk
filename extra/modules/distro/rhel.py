distro = 'red hat enterprise linux (server|desktop)'
pybin = '/usr/bin/python'
script['pre'] = """#!/bin/bash
touch /root/BDISK
"""
script['post'] = """#!/bin/bash
rm -f /root/BDISK
"""
pkg['pre'] = ['yum', 'makecache']
pkg['install'] = ['yum', '-y', 'install', '%PKG%']
pkg['check'] = ['rpm', '-qi', '%PKG']
