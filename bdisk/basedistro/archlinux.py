#!/usr/bin/env python3

# Supported initsys values:
# systemd
# Possible future inclusions:
# openrc
# runit
# sinit
# s6
# shepherd
initsys = 'systemd'

def extern_prep(cfg, cur_arch = 'x86_64'):
    import os
    import re
    mirrorlist = os.path.join(cfg['build']['paths']['chroot'],
                              cur_arch,
                              'etc/pacman.d/mirrorlist')
    with open(mirrorlist, 'r') as f:
        mirrors = []
        for i in f.readlines():
            m = re.sub('^\s*#.*$', '', i.strip())
            if m != '':
                mirrors.append(m)
    if not mirrors:
        # We do this as a fail-safe.
        mirror = ('\n\n# Added by BDisk\n'
                  'Server = https://arch.mirror.square-r00t.net/'
                  '$repo/os/$arch\n')
        with open(mirrorlist, 'a') as f:
            f.write(mirror)
    return()

# This will be run before the regular packages are installed. It can be
# whatever script you like, as long as it has the proper shebang and doesn't
# need additional packages installed.
# In Arch's case, we use it for initializing the keyring and installing an AUR
# helper.
pkg_mgr_prep = """#!/bin/bash

pacman -Syy
pacman-key --init
pacman-key --populate archlinux
pacman -S --noconfirm --needed base
pacman -S --noconfirm --needed base-devel multilib-devel git linux-headers \
                               mercurial subversion vala xorg-server-devel
cd /tmp
sqrt="https://git.square-r00t.net/BDisk/plain/external"
# Temporary until there's another AUR helper that allows dropping privs AND
# automatically importing GPG keys.
pkg="${sqrt}/apacman-current.pkg.tar.xz?h=4.x_rewrite"
curl -sL -o apacman-current.pkg.tar.xz ${pkg}
pacman -U --noconfirm apacman-current.pkg.tar.xz
rm apacman*
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
            'sys_update': ['/usr/bin/apacman', '-S', '-u'],
            'sync_cmd': ['/usr/bin/apacman', '-S', '-y', '-y'],
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
           'syslinux', 'traceroute', 'vi']

