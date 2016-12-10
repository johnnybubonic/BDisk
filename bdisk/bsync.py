import shutil
import os
import pwd
import grp
import datetime
import git
import subprocess


def http(conf):
    http = conf['http']
    build = conf['build']
    tempdir = build['tempdir']
    arch = build['arch']
    bdisk = conf['bdisk']
    if conf['sync']['http']:
        uid = pwd.getpwnam(http['user'])[2]
        gid = grp.getgrnam(http['group'])[2]
        httpdir = http['path']
        archboot = build['archboot']
        # remove the destination if it exists
        if os.path.isdir(httpdir):
            print('{0}: Removing {1} in preparation of syncing. Please wait...'.format(
                                                                    datetime.datetime.now(),
                                                                    httpdir))
            shutil.rmtree(httpdir)
        # just to make it again. we do this to avoid file existing conflicts.
        os.makedirs(httpdir)
        # here we build a dict of files to copy and their destination paths.
        httpfiles = {}
        print('{0}: Now syncing files to {1}. Please wait...'.format(
                                                            datetime.datetime.now(),
                                                            httpdir))
        for a in arch:
            for i in ('md5', 'sfs', 'sha256'):
                httpfiles['{0}/{1}/airootfs.{2}'.format(bdisk['name'], a, i)] = '{0}/{1}/airootfs.{2}'.format(bdisk['name'], a, i)
        httpfiles['VERSION_INFO.txt'] = 'VERSION_INFO.txt'
        if 'x86_64' in arch:
            httpfiles['boot/{0}.64.kern'.format(bdisk['uxname'])] = '{0}.kern'.format(bdisk['uxname'])
            httpfiles['boot/{0}.64.img'.format(bdisk['uxname'])] = '{0}.img'.format(bdisk['uxname'])
        if 'i686' in arch:
            httpfiles['boot/{0}.32.kern'.format(bdisk['uxname'])] = '{0}.32.kern'.format(bdisk['uxname'])
            httpfiles['boot/{0}.32.img'.format(bdisk['uxname'])] = '{0}.32.img'.format(bdisk['uxname'])
        httpfiles['{0}.png'.format(bdisk['uxname'])] = '{0}.png'.format(bdisk['uxname'])
        # and now the magic.
        for k in httpfiles.keys():
            destpath = httpfiles[k]
            fulldest = '{0}/{1}'.format(httpdir, destpath)
            parentdir = os.path.split(fulldest)[0]
            os.makedirs(parentdir, exist_ok = True)
            shutil.copy2('{0}/{1}'.format(tempdir, k), '{0}/{1}'.format(httpdir, httpfiles[k]))
        for root, dirs, files in os.walk(httpdir):
            for d in dirs:
                os.chown(os.path.join(root, d), uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)

def tftp(conf):
    # TODO: pxelinux cfg
    tftp = conf['tftp']
    build = conf['build']
    tempdir = build['tempdir']
    arch = build['arch']
    bdisk = conf['bdisk']
    if conf['sync']['tftp']:
        uid = pwd.getpwnam(tftp['user'])[2]
        gid = grp.getgrnam(tftp['group'])[2]
        tftpdir = tftp['path']
        # remove the destination if it exists
        if os.path.isdir(tftpdir):
            print('{0}: Removing {1} in preparation of syncing. Please wait...'.format(
                                                                        datetime.datetime.now(),
                                                                        tftpdir))
            shutil.rmtree(tftpdir)
        # and we make it again
        os.makedirs(httpdir)
        # and make a dict of the files etc.
        tftpfiles = {}
        print('{0}: Now syncing files to {1}. Please wait...'.format(
                                                            datetime.datetime.now(),
                                                            tftpdir))
        for a in arch:
            for i in ('md5', 'sfs', 'sha256'):
                tftpfiles['{0}/{1}/airootfs.{2}'.format(bdisk['name'], a, i)] = '{0}/{1}/airootfs.{2}'.format(bdisk['name'], a, i)
        tftpfiles['VERSION_INFO.txt'] = 'VERSION_INFO.txt'
        if 'x86_64' in arch:
            tftpfiles['boot/{0}.64.kern'.format(bdisk['uxname'])] = '{0}.kern'.format(bdisk['uxname'])
            tftpfiles['boot/{0}.64.img'.format(bdisk['uxname'])] = '{0}.img'.format(bdisk['uxname'])
        if 'i686' in arch:
            tftpfiles['boot/{0}.32.kern'.format(bdisk['uxname'])] = '{0}.32.kern'.format(bdisk['uxname'])
            tftpfiles['boot/{0}.32.img'.format(bdisk['uxname'])] = '{0}.32.img'.format(bdisk['uxname'])
        tftpfiles['{0}.png'.format(bdisk['uxname'])] = '{0}.png'.format(bdisk['uxname'])
        # and now the magic.
        for k in tftpfiles.keys():
            destpath = tftpfiles[k]
            fulldest = '{0}/{1}'.format(tftpdir, destpath)
            parentdir = os.path.split(fulldest)[0]
            os.makedirs(parentdir, exist_ok = True)
            shutil.copy2('{0}/{1}'.format(tempdir, k), '{0}/{1}'.format(tftpdir, tftpfiles[k]))
        for root, dirs, files in os.walk(tftpdir):
            for d in dirs:
                os.chown(os.path.join(root, d), uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)

def git(conf):
    build = conf['build']
    git_name = conf['bdisk']['dev']
    git_email = conf['bdisk']['email']
    if conf['sync']['git']:
        print('{0}: Creating a commit. Please wait...'.format(datetime.datetime.now()))
        repo = git.Repo(build['basedir'])
        repo.git.add('--all')
        repo.index.commit("automated commit from BDisk (git:sync)")
        print('{0}: Pushing to the remote. Please wait...'.format(datetime.datetime.now()))
        repo.remotes.origin.push()


def rsync(conf):
    build = conf['build']
    tempdir = build['tempdir']
    rsync = conf['rsync']
    sync = conf['sync']
    server = rsync['host']
    path = rsync['path']
    user = rsync['user']
    locpath = False
    if sync['rsync']:
        # TODO: some sort of debugging/logging
        cmd = ['/usr/bin/rsync',
                '-a',
                '-q',
                locpath,
                '{0}@{1}:{2}/.'.format(user, server, path)]
        if sync['http']:
            cmd[3] = conf['http']['path']
            print('{0}: Syncing {1} to {2}. Please wait...'.format(
                                                    datetime.datetime.now(),
                                                    cmd[4],
                                                    server))
            subprocess.call(cmd)
        if sync['tftp']:
            cmd[3] = conf['tftp']['path']
            print('{0}: Syncing {1} to {2}. Please wait...'.format(
                                                    datetime.datetime.now(),
                                                    cmd[4],
                                                    server))
            subprocess.call(cmd)
        if conf['ipxe']:
            cmd[3] = build['archboot']
            print('{0}: Syncing {1} to {2}. Please wait...'.format(
                                                    datetime.datetime.now(),
                                                    cmd[4],
                                                    server))
            subprocess.call(cmd)
        cmd[3] = isodir
        print('{0}: Syncing {1} to {2}. Please wait...'.format(
                                                    datetime.datetime.now(),
                                                    cmd[4],
                                                    server))
        subprocess.call(cmd)
        # Now we copy some extra files.
        prebuild_dir = '{0}/extra/pre-build.d/'
        rsync_files = ['{0}/VERSION_INFO.txt'.format(tempdir),
                        '{0}/root/packages.both'.format(prebuild_dir),
                        '{0}/root/iso.pkgs.both'.format(prebuild_dir)]
        for x in rsync_files:
            cmd[3] = x
            print('{0}: Syncing {1} to {2}. Please wait...'.format(
                                                        datetime.datetime.now(),
                                                        cmd[4],
                                                        server))
        # And we grab the remaining, since we need to rename them.
        print('{0}: Syncing some extra files to {1}. Please wait...'.format(
                                                        datetime.datetime.now(),
                                                        server))
        for a in arch:
            cmd[3] = '{0}/{1}/root/packages.arch'.format(prebuild_dir, a)
            cmd[4] = '{0}@{1}:{2}/packages.{3}'.format(user, server, path, a)
            subprocess.call(cmd)
            cmd[3] = '{0}/{1}/root/iso.pkgs.arch'.format(prebuild_dir, a)
            cmd[4] = '{0}@{1}:{2}/iso.pkgs.{3}'.format(user, server, path, a)
            subprocess.call(cmd)
