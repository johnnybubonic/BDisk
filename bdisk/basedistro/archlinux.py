#!/usr/bin/env python3.6

# Supported initsys values:
# systemd
# Possible future inclusions:
# openrc
# runit
# sinit
# s6
# shepherd
initsys = 'systemd'

# This will be run before the regular packages are installed. It can be
# whatever script you like, as long as it has the proper shebang and doesn't
# need additional packages installed.
pkg_mgr_prep = """#!/bin/bash

"""

# Special values:
# {PACKAGE} = the package name
# {VERSION} = the version specified in the <package version= ...> attribute
# {REPO} = the repository specified in the <package repo= ...> attribute
# If check_cmds are needed to run before installing, set pre_check to True.
# Return code 0 means the package is installed already, anything else means we
# should try to install it.
#### AUR SUPPORT ####
packager = {'pre_check': False,
            'sys_update': ['/usr/bin/aurman', '-S', '-u'],
            'sync_cmd': ['/usr/bin/aurman', '-S', '-y', '-y'],
            'check_cmds': {'versioned': ['/usr/bin/pacman',
                                         '-Q', '-s',
                                         '{PACKAGE}'],
                           'unversioned': ['/usr/bin/pacman',
                                           '-Q', '-s',
                                           '{PACKAGE}']
                           },
            'update_cmds': {'versioned': ['/usr/bin/pacman',
                                          '-S', '-u',
                                          '{PACKAGE}'],
                            'unversioned': ['/usr/bin/pacman',
                                            '-S', '-u',
                                            '{PACKAGE}']
                            },
            }

# These are packages *required* to exist on the base guest, no questions asked.
# TODO: can this be trimmed down?
prereqs = ['arch-install-scripts', 'archiso', 'bzip2', 'coreutils',
           'customizepkg-scripting', 'cronie', 'dhclient', 'dhcp', 'dhcpcd',
           'dosfstools', 'dropbear', 'efibootmgr', 'efitools', 'efivar',
           'file', 'findutils', 'iproute2', 'iputils', 'libisoburn',
           'localepurge', 'lz4', 'lzo', 'lzop', 'mkinitcpio-nbd',
           'mkinitcpio-nfs-utils', 'mkinitcpio-utils', 'nbd', 'ms-sys',
           'mtools', 'net-tools', 'netctl', 'networkmanager', 'pv',
           'python', 'python-pyroute2', 'rsync', 'sed', 'shorewall',
           'squashfs-tools', 'sudo', 'sysfsutils',
           'syslinux', 'traceroute']

