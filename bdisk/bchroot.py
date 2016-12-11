import os
import sys
import psutil
import subprocess
import datetime
import tarfile
import humanize
import shutil


def chroot(chrootdir, chroot_hostname, cmd = '/root/pre-build.sh'):
    # MOUNT the chroot
    mountpoints = psutil.disk_partitions(all = True)
    mounts = []
    for m in mountpoints:
        mounts.append(m.mountpoint)
    cmounts = {}
    for m in ('chroot', 'resolv', 'proc', 'sys', 'efi', 'dev', 'pts', 'shm', 'run', 'tmp'):
        cmounts[m] = None
    # chroot (bind mount... onto itself. it's so stupid, i know. see https://bugs.archlinux.org/task/46169)
    if chrootdir not in mounts:
        cmounts['chroot'] = ['/bin/mount',
                            '--bind',
                            chrootdir,
                            chrootdir]
    # resolv 
    if (chrootdir + '/etc/resolv.conf') not in mounts:
        cmounts['resolv'] = ['/bin/mount',
                            '--bind',
                            '-o', 'ro',
                            '/etc/resolv.conf',
                            chrootdir + '/etc/resolv.conf']
    # proc
    if (chrootdir + '/proc') not in mounts:
        cmounts['proc'] = ['/bin/mount',
                            '-t', 'proc',
                            '-o', 'nosuid,noexec,nodev',
                            'proc',
                            chrootdir + '/proc']
    # sys
    if (chrootdir + '/sys') not in mounts:
        cmounts['sys'] = ['/bin/mount',
                            '-t', 'sysfs',
                            '-o', 'nosuid,noexec,nodev,ro',
                            'sys',
                            chrootdir + '/sys']
    # efi (if it exists on the host)
    if '/sys/firmware/efi/efivars' in mounts:
        if (chrootdir + '/sys/firmware/efi/efivars') not in mounts:
            cmounts['efi'] = ['/bin/mount',
                            '-t', 'efivarfs',
                            '-o', 'nosuid,noexec,nodev',
                            'efivarfs',
                            chrootdir + '/sys/firmware/efi/efivars']
    # dev
    if (chrootdir + '/dev') not in mounts:
        cmounts['dev'] = ['/bin/mount',
                            '-t', 'devtmpfs',
                            '-o', 'mode=0755,nosuid',
                            'udev',
                            chrootdir + '/dev']
    # pts
    if (chrootdir + '/dev/pts') not in mounts:
        cmounts['pts'] = ['/bin/mount',
                            '-t', 'devpts',
                            '-o', 'mode=0620,gid=5,nosuid,noexec',
                            'devpts',
                            chrootdir + '/dev/pts']
    # shm (if it exists on the host)
    if '/dev/shm' in mounts:
        if (chrootdir + '/dev/shm') not in mounts:
            cmounts['shm'] = ['/bin/mount',
                            '-t', 'tmpfs',
                            '-o', 'mode=1777,nosuid,nodev',
                            'shm',
                            chrootdir + '/dev/shm']
    # run (if it exists on the host)
    if '/run' in mounts:
        if (chrootdir + '/run') not in mounts:
            cmounts['run'] = ['/bin/mount',
                            '-t', 'tmpfs',
                            '-o', 'nosuid,nodev,mode=0755',
                            'run',
                            chrootdir + '/run']
    # tmp (if it exists on the host)
    if '/tmp' in mounts:
        if (chrootdir + '/tmp') not in mounts:
            cmounts['tmp'] = ['/bin/mount',
                            '-t', 'tmpfs',
                            '-o', 'mode=1777,strictatime,nodev,nosuid',
                            'tmp',
                            chrootdir + '/tmp']
    # the order we mount here is VERY IMPORTANT. Sure, we could do "for m in cmounts:", but dicts aren't ordered until python 3.6
    # and this is SO important it's best that we be explicit as possible while we're still in alpha/beta stage. TODO?
    for m in ('chroot', 'resolv', 'proc', 'sys', 'efi', 'dev', 'pts', 'shm', 'run', 'tmp'):
        if cmounts[m]:
            subprocess.call(cmounts[m])
    print("{0}: [CHROOT] Running '{1}' ({2}). PROGRESS: tail -f {2}/var/log/chroot_install.log ...".format(
                                                    datetime.datetime.now(),
                                                    cmd,
                                                    chrootdir))
    real_root = os.open("/", os.O_RDONLY)
    os.chroot(chrootdir)
    os.system('/root/pre-build.sh')
    os.fchdir(real_root)
    os.chroot('.')
    os.close(real_root)
    return(chrootdir)

def chrootUnmount(chrootdir):
    subprocess.call(['umount', '-lR', chrootdir])

def chrootTrim(build):
    chrootdir = build['chrootdir']
    arch = build['arch']
    for a in arch:
        # Compress the pacman and apacman caches.
        for i in ('pacman', 'apacman'):
            shutil.rmtree('{0}/root.{1}/var/cache/{2}'.format(chrootdir, a, i))
            os.makedirs('{0}/root.{1}/usr/local/{2}'.format(chrootdir, a, i), exist_ok = True)
            tarball = '{0}/root.{1}/usr/local/{2}/{2}.db.tar.xz'.format(chrootdir, a, i)
            dbdir = '{0}/root.{1}/var/lib/{2}/local'.format(chrootdir, a, i)
            if os.path.isdir(dbdir):
                print("{0}: [CHROOT] Compressing {1}'s cache ({2})...".format(
                                                        datetime.datetime.now(),
                                                        chrootdir,
                                                        a))
                if os.path.isfile(tarball):
                    os.remove(tarball)
                with tarfile.open(name = tarball, mode = 'w:xz') as tar:  # if this complains, use x:xz instead
                    tar.add(dbdir, arcname = os.path.basename(dbdir))
                shutil.rmtree(dbdir, ignore_errors = True)
                print("{0}: [CHROOT] Created {1} ({2}). {3} cleared.".format(
                                                        datetime.datetime.now(),
                                                        tarball,
                                                        humanize.naturalsize(
                                                            os.path.getsize(tarball)),
                                                        dbdir))
        # TODO: move the self-cleanup in pre-build.sh to here.
        delme = ['/root/.gnupg',
                '/root/.bash_history',
                #'/var/log/chroot_install.log',  # disable for now. maybe always disable if debug is enabled? TODO.
                '/.git',
                '/root/.viminfo']
        for i in delme:
            fullpath = '{0}/root.{1}{2}'.format(chrootdir, a, i)
            if os.path.isfile(fullpath):
                os.remove(fullpath)
            elif os.path.isdir(fullpath):
                shutil.rmtree(fullpath, ignore_errors = True)
