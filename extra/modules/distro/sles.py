distro = 'suse linux enterprise server'
pybin = '/usr/bin/python'
script['pre'] = """#!/bin/bash
touch /root/BDISK
"""
script['post'] = """#!/bin/bash
rm -f /root/BDISK
"""
pkg['pre'] = ['zypper', 'refresh']
pkg['install'] = ['zypper', 'install', '--no-confirm', '-l', '%PKG%']
pkg['check'] = ['rpm', '-qi', '%PKG']
