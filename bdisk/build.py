import os
import tarfile
import shutil
import glob


def chrootClean(build):
    chrootdir = build['chrootdir']
    arch = build['arch']
    backupdir = build['dlpath'] + '/' + 'bak'
    os.makedirs(backupdir, exist_ok = True)
    ## Save some stuff that needs to be retained.
    # Compress the pacman cache.
    for a in arch:
        os.makedirs(chrootdir + '/root.' + a + '/usr/local/pacman', exist_ok = True)
        tarball = chrootdir + '/root.' + a + '/usr/local/pacman/pacman.db.tar.xz'
        dbdir = chrootdir + '/root.' + a + '/var/lib/pacman/local'
        print("Now cleaning {0}/root.{1}. Please wait...".format(chrootdir, a))
        if os.path.isfile(tarball):
            os.remove(tarball)
        with tarfile.open(name = tarball, mode = 'w:xz') as tar:  # if this balks, try x:xz
            tar.add(dbdir, arcname = os.path.basename(dbdir))
        # Cut out the fat
        # The following are intended as "overrides" of the paths we'll be deleting.
        backup = {}
        backup['dirs'] = ['/var/lib/pacman/local']
        backup['files'] = ['/usr/share/locale/locale.alias',
                        '/usr/share/zoneinfo/EST5EDT',
                        '/usr/share/zoneinfo/UTC',
                        '/usr/share/locale/en',
                        '/usr/share/locale/en_US',
                        '/usr/share/locale/en_GB']
        # And these are what we remove.
        delete = {}
        delete['dirs'] = ['/usr/share/locale/*',
                        '/var/cache/pacman/*',
                        '/var/cache/pkgfile/*',
                        '/var/cache/apacman/pkg/*',
                        '/var/lib/pacman/*',
                        '/var/abs/local/yaourtbuild/*',
                        '/usr/share/zoneinfo',
                        '/root/.gnupg',
                        '/tmp/*',
                        '/var/tmp/*',
                        '/var/abs/*',
                        '/run/*',
                        '/boot/*',
                        '/usr/src/*',
                        '/var/log/*',
                        '/.git']
        delete['files'] = ['/root/.bash_history',
                        '/root/apacman*',
                        '/root/iso.pkgs*',
                        '/root/packages.*',
                        '/root/pre-build.sh',
                        '/root/.viminfo',
                        '/root/.bashrc']
        # First we backup files. We don't need to create backup['dirs']
        # since they should be empty. If not, they go in backup['files'].
        for f in backup['files']:
            #os.makedirs(backupdir + '/root.' + a + os.path.dirname(f), exist_ok = True)
            #shutil.copy2(chrootdir + '/root.' + a + f, backupdir + '/root.' + a + f)
            for root, dirs, files in os.walk(f):
                for item in files:
                    src_path = os.path.join(root, item)
                    dst_path = os.path.join(backupdir + '/root.' + a, src_path.replace(f, ''))
                    if os.path.exists(dst_path):
                        if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                            shutil.copy2(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
                for item in dirs:
                    src_path = os.path.join(root, item)
                    dst_path = os.path.join(backupdir + '/root.' + a, src_path.replace(f, ''))
                    os.makedirs(dst_path, exist_ok = True)
        # Now we delete the above.
        for f in delete['files']:
            for x in glob.glob(chrootdir + '/root.' + a + f):
                os.remove(x)
        for d in delete['dirs']:
            for x in glob.glob(chrootdir + '/root.' + a + d):
                #os.remove(x)
                shutil.rmtree(x)
        # And restore the dirs/files
        for d in backup['dirs']:
            os.makedirs(chrootdir + '/root.' + a + d, exist_ok = True)
        for f in backup['files']:
            #os.makedirs(chrootdir + '/root.' + a + os.path.dirname(f), exist_ok = True)
            #shutil.copy2(backupdir + '/root.' + a + f, chrootdir + '/root.' + a + f)
            for root, dirs, files in os.walk(f):
                for item in files:
                    src_path = os.path.join(backupdir + '/root.' + a, src_path.replace(f, ''))
                    dst_path = os.path.join(root, item)
                    if os.path.exists(dst_path):
                        if os.stat(src_path).st_mtime > os.stat(dst_path).st_mtime:
                            shutil.copy2(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
                for item in dirs:
                    src_path = os.path.join(backupdir + '/root.' + a, src_path.replace(f, ''))
                    dst_path = os.path.join(root, item)
                    os.makedirs(dst_path, exist_ok = True)
        #shutil.rmtree(backupdir)

def genImg():
    pass

def genUEFI():
    pass

def genISO():
    pass
