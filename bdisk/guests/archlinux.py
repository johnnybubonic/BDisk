#!/usr/bin/env python3

import os
from .. import utils  # LOCAL # do i need to escalate two levels up?

class Manifest(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.name = 'archlinux'
        self.version = None  # rolling release
        self.release = None  # rolling release
        # https://www.archlinux.org/master-keys/
        # Pierre Schmitz. https://www.archlinux.org/people/developers/#pierre
        self.gpg_authorities = ['4AA4767BBC9C4B1D18AE28B77F2D434B9741E8AC']
        self.tarball = None
        self.sig = None
        self.mirror = None
        self.checksum = {'sha1': None,
                         'md5': None}
        self.verified = False
        self.arches = ('x86_64', )
        self.bootsupport = ('uefi', 'bios', 'pxe', 'ipxe', 'iso')
        self.kernel = '/boot/vmlinuz-linux'
        self.initrd = '/boot/initramfs-linux.img'
        # TODO: can this be trimmed down?
        self.prereqs = ['arch-install-scripts', 'archiso', 'bzip2', 'coreutils', 'customizepkg-scripting', 'cronie',
                        'dhclient', 'dhcp', 'dhcpcd', 'dosfstools', 'dropbear', 'efibootmgr', 'efitools', 'efivar',
                        'file', 'findutils', 'iproute2', 'iputils', 'libisoburn', 'localepurge', 'lz4', 'lzo',
                        'lzop', 'mkinitcpio-nbd', 'mkinitcpio-nfs-utils', 'mkinitcpio-utils', 'nbd', 'ms-sys',
                        'mtools', 'net-tools', 'netctl', 'networkmanager', 'pv', 'python', 'python-pyroute2',
                        'rsync', 'sed', 'shorewall', 'squashfs-tools', 'sudo', 'sysfsutils', 'syslinux',
                        'traceroute', 'vi']
        self._get_filenames()

    def _get_filenames(self):
        # TODO: cache this info
        webroot = 'iso/latest'
        for m in self.cfg['mirrors']:
            uri = os.path.join(m, webroot)
            try:
                self.tarball = utils.detect().remote_files(uri, regex = ('archlinux-'
                                                                         'bootstrap-'
                                                                         '[0-9]{4}\.'
                                                                         '[0-9]{2}\.'
                                                                         '[0-9]{2}-'
                                                                         'x86_64\.tar\.gz$'))[0]
                self.sig = '{0}.sig'.format(self.tarball)
                for h in self.checksum:
                    self.checksum[h] = os.path.join(uri, '{0}sums.txt'.format(h))
                self.mirror = m
                break
            except Exception as e:
                pass
        if not self.tarball:
            raise ValueError('Could not find the tarball URI. Check your network connection.')
        return()


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
