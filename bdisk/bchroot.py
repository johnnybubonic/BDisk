# NOTE: this is almost taken verbatim from https://github.com/pkgcore/pychroot's
# pychroot/scripts/pychroot.py because the pychroot.Chroot method isn't really
# documented very well

#from __future__ import absolute_import, unicode_literals

#from functools import partial
import os
import sys
import psutil
#from pychroot.base import Chroot
import pychroot
import subprocess

#class mountpoints(argparse.Action):
#
#    def __call__(self, parser, namespace, values, option_string=None):
#        if not getattr(namespace, 'mountpoints', False):
#            namespace.mountpoints = {}
#        namespace.mountpoints.update(values)

def chroot(chrootdir, chroot_hostname, cmd = '/root/pre-build.sh'):
    # MOUNT the chroot
    mountpoints = psutil.disk_partitions(all = True)
    mounts = []
    for m in mountpoints:
        mounts.append(m.mountpoint)
    cmnts = {}
    # mount the chrootdir... onto itself. as a bind mount. it's so stupid, i know. see https://bugs.archlinux.org/task/46169
    if chrootdir not in mounts:
        #cmnts[chrootdir + ':' + chrootdir] = {'recursive': False, 'readonly': False, 'create': False}
        cmnts[chrootdir + ':/'] = {'recursive': False, 'readonly': False, 'create': False}

    # mount -t proc to chrootdir + '/proc' here
    if (chrootdir + '/proc') not in mounts:
        cmnts['proc:/proc'] = {'recursive': True, 'create': True}

    # rbind mount /sys to chrootdir + '/sys' here
    if (chrootdir + '/sys') not in mounts:
        #cmnts['/sys:/sys'] = {'recursive': True, 'create': True}  # if the below doesn't work, try me. can also try ['sysfs:/sys']
        cmnts['/sys'] = {'recursive': True, 'create': True}

    # rbind mount /dev to chrootdir + '/dev' here
    if (chrootdir + '/dev') not in mounts:
        cmnts['/dev'] = {'recursive': True, 'create': True}

    # mount the efivars in the chroot if it exists on the host. i mean, why not?
    if '/sys/firmware/efi/efivars' in mounts:
        if (chrootdir + '/sys/firmware/efi/efivars') not in mounts:
            cmnts['/sys/firmware/efi/efivars'] = {'recursive': True}

    if '/run' in mounts:
        if (chrootdir + '/run') not in mounts:
            cmnts['/run'] = {'recursive': True}

    pychroot.base.Chroot.default_mounts = {}
    chroot = pychroot.base.Chroot(chrootdir, mountpoints = cmnts, hostname = chroot_hostname)
    chroot.mount()
    with chroot:
        import os
        os.system(cmd)
    chroot.cleanup()
    return(chrootdir, cmnts)

#def chrootUnmount(chrootdir, cmnts):
def chrootUnmount(chrootdir):
    # TODO: https://github.com/pkgcore/pychroot/issues/22 try to do this more pythonically. then we can remove subprocess
    subprocess.call(['umount', '-lR', chrootdir])
