import os
import sys
import psutil
import subprocess
import ctypes


def chrootMount(source, target, fs, options=''):
    ret = ctypes.CDLL('libc.so.6', use_errno=True).mount(source, target, fs, 0, options)
    if ret < 0:
        errno = ctypes.get_errno()
        raise RuntimeError("Error mounting {} ({}) on {} with options '{}': {}".
                        format(source, fs, target, options, os.strerror(errno)))

def chroot(chrootdir, chroot_hostname, cmd = '/root/pre-build.sh'):
    # MOUNT the chroot
    mountpoints = psutil.disk_partitions(all = True)
    mounts = []
    for m in mountpoints:
        mounts.append(m.mountpoint)
    # mount the chrootdir... onto itself. as a bind mount. it's so stupid, i know. see https://bugs.archlinux.org/task/46169
    if chrootdir not in mounts:
        subprocess.call(['/bin/mount', '--bind', chrootdir, chrootdir])
### The following mountpoints don't seem to mount properly with pychroot. save it for v3.n+1. TODO. ###
    # bind-mount so we can resolve things inside
    if (chrootdir + '/etc/resolv.conf') not in mounts:
        subprocess.call(['/bin/mount', '--bind', '-o', 'ro', '/etc/resolv.conf', chrootdir + '/etc/resolv.conf'])
    # mount -t proc to chrootdir + '/proc' here
    if (chrootdir + '/proc') not in mounts:
        subprocess.call(['/bin/mount', '-t', 'proc', '-o', 'nosuid,noexec,nodev', 'proc', chrootdir + '/proc'])
    # rbind mount /sys to chrootdir + '/sys' here
    if (chrootdir + '/sys') not in mounts:
        subprocess.call(['/bin/mount', '-t', 'sysfs', '-o', 'nosuid,noexec,nodev,ro', 'sys', chrootdir + '/sys'])
    # mount the efivars in the chroot if it exists on the host. i mean, why not?
    if '/sys/firmware/efi/efivars' in mounts:
        if (chrootdir + '/sys/firmware/efi/efivars') not in mounts:
            subprocess.call(['/bin/mount', '-t', 'efivarfs', '-o', 'nosuid,noexec,nodev', 'efivarfs', chrootdir + '/sys/firmware/efi/efivars'])
    # rbind mount /dev to chrootdir + '/dev' here
    if (chrootdir + '/dev') not in mounts:
        subprocess.call(['/bin/mount', '-t', 'devtmpfs', '-o', 'mode=0755,nosuid', 'udev', chrootdir + '/dev'])
    if (chrootdir + '/dev/pts') not in mounts:
        subprocess.call(['/bin/mount', '-t', 'devpts', '-o', 'mode=0620,gid=5,nosuid,noexec', 'devpts', chrootdir + '/dev/pts'])
    if '/dev/shm' in mounts:
        if (chrootdir + '/dev/shm') not in mounts:
            subprocess.call(['/bin/mount', '-t', 'tmpfs', '-o', 'mode=1777,nosuid,nodev', 'shm', chrootdir + '/dev/shm'])
    if '/run' in mounts:
        if (chrootdir + '/run') not in mounts:
            subprocess.call(['/bin/mount', '-t', 'tmpfs', '-o', 'nosuid,nodev,mode=0755', 'run', chrootdir + '/run'])
    if '/tmp' in mounts:
        if (chrootdir + '/tmp') not in mounts:
            subprocess.call(['/bin/mount', '-t', 'tmpfs', '-o', 'mode=1777,strictatime,nodev,nosuid', 'tmp', chrootdir + '/tmp'])

    print("Performing '{0}' in chroot for {1}...".format(cmd, chrootdir))
    print("You can view the progress via:\n\n\ttail -f {0}/var/log/chroot_install.log\n".format(chrootdir))
    real_root = os.open("/", os.O_RDONLY)
    os.chroot(chrootdir)
    os.system('locale-gen > /dev/null 2>&1')
    os.system('/root/pre-build.sh')
    os.fchdir(real_root)
    os.chroot('.')
    os.close(real_root)
    return(chrootdir)

def chrootUnmount(chrootdir):
    subprocess.call(['umount', '-lR', chrootdir])
