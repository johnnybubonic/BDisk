distro = 'arch'
pybin = '/usr/bin/python'
script['pre'] = """#!/bin/bash
touch /root/BDISK
"""
script['post'] = """#!/bin/bash
rm -f /root/BDISK
"""
pkg['pre'] = ['pacman', '-Syyy']
pkg['install'] = ['apacman', '-S', '%PKG%']
pkg['check'] = ['pacman', '-Q', '%PKG']
