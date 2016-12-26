import os
import shutil
import re
import hashlib
import tarfile
import subprocess
import re
import jinja2
import datetime
import humanize
from urllib.request import urlopen
import host  # bdisk.host
import bGPG  # bdisk.bGPG


def dirChk(config_dict):
    # Make dirs if they don't exist
    for d in ('archboot', 'isodir', 'mountpt', 'srcdir', 'prepdir'):
        os.makedirs(config_dict['build'][d], exist_ok = True)
    # Make dirs for sync staging if we need to
    for x in ('http', 'tftp'):
        if config_dict['sync'][x]:
            os.makedirs(config_dict[x]['path'], exist_ok = True)

def downloadTarball(conf):
    build = conf['build']
    dlpath = build['dlpath']
    arch = build['arch']
    #mirror = 'http://mirrors.kernel.org/archlinux'
    mirror = build['mirrorproto'] + '://' + build['mirror']
    rlsdir = mirror + build['mirrorpath']
    sha_in = urlopen(mirror + build['mirrorchksum'])
    # returns path/filename e.g. /some/path/to/file.tar.gz
    # we use .gnupg since we'll need it later.
    os.makedirs(dlpath + '/.gnupg', exist_ok = True)
    tarball_path = {}
    for x in arch:
        tarball_path[x] = dlpath + '/.latest.' + x + '.tar'
    sha1sums = sha_in.read()
    sha_in.close()
    sha_raw = sha1sums.decode("utf-8")
    sha_list = list(filter(None, sha_raw.split('\n')))
    sha_dict = {x.split()[1]: x.split()[0] for x in sha_list}
    # all that lousy work just to get a sha1 sum. okay. so.
    for a in arch:
        pattern = re.compile('^.*' + a + '\.tar(\.(gz|bz2|xz))?$')
        tarball = [filename.group(0) for l in list(sha_dict.keys()) for filename in [pattern.search(l)] if filename][0]
        sha1 = sha_dict[tarball]
        if os.path.isfile(tarball_path[a]):
            pass
        else:
            # fetch the tarball...
            print("{0}: [PREP] Fetching tarball ({1} architecture)...".format(
                                                            datetime.datetime.now(),
                                                            a))
            #dl_file = urllib.URLopener()
            tarball_dl = urlopen(rlsdir + tarball)
            with open(tarball_path[a], 'wb') as f:
                f.write(tarball_dl.read())
            tarball_dl.close()
            print("{0}: [PREP] Done fetching {1} ({2}).".format(
                                                    datetime.datetime.now(),
                                                    tarball_path[a],
                                                    humanize.naturalsize(
                                                        os.path.getsize(tarball_path[a]))))
        print("{0}: [PREP] Checking hash checksum {1} against {2}...".format(
                                                    datetime.datetime.now(),
                                                    sha1,
                                                    tarball_path[a]))
        tarball_hash = hashlib.sha1(open(tarball_path[a], 'rb').read()).hexdigest()
        if tarball_hash != sha1:
            exit(("{0}: {1} either did not download correctly\n\t\t\t    or a wrong (probably old) version exists on the filesystem.\n\t\t\t    " +
                                "Please delete it and try again.").format(datetime.datetime.now(), tarball))
        elif build['mirrorgpgsig'] != '':
            # okay, so the sha1 matches. let's verify the signature.
            if build['mirrorgpgsig'] == '.sig':
                gpgsig_remote = rlsdir + tarball + '.sig'
            else:
                gpgsig_remote = build['mirrorgpgsig']
            sig_dl = urlopen(gpgsig_remote)
            sig = tarball_path[a] + '.sig'
            with open(sig, 'wb+') as f:
                f.write(sig_dl.read())
            sig_dl.close()
            gpg_verify = bGPG.gpgVerify(sig, tarball_path[a], conf)
            if not gpg_verify:
                exit("{0}: There was a failure checking {1} against {2}. Please investigate.".format(
                                                                    datetime.datetime.now(),
                                                                    sig,
                                                                    tarball_path[a]))
    return(tarball_path)

def unpackTarball(tarball_path, build, keep = False):
    chrootdir = build['chrootdir']
    if os.path.isdir(chrootdir):
        if not keep:
            # Make the dir if it doesn't exist
            shutil.rmtree(chrootdir, ignore_errors = True)
            os.makedirs(chrootdir, exist_ok = True)
    else:
        os.makedirs(chrootdir, exist_ok = True)
    # Open and extract the tarball
    if not keep:
        for a in build['arch']:
            print("{0}: [PREP] Extracting tarball {1} ({2})...".format(
                                                            datetime.datetime.now(),
                                                            tarball_path[a],
                                                            humanize.naturalsize(
                                                                os.path.getsize(tarball_path[a]))))
            tar = tarfile.open(tarball_path[a], 'r:gz')
            tar.extractall(path = chrootdir)
            tar.close()
            print("{0}: [PREP] Extraction for {1} finished.".format(datetime.datetime.now(), tarball_path[a]))

def buildChroot(conf, keep = False):
    build = conf['build']
    bdisk = conf['bdisk']
    user = conf['user']
    dlpath = build['dlpath']
    chrootdir = build['chrootdir']
    arch = build['arch']
    extradir = build['basedir'] + '/extra'
    unpack_me = unpackTarball(downloadTarball(conf), build, keep)
    # build dict of lists of files and dirs from pre-build.d dir, do the same with arch-specific changes.
    prebuild_overlay = {}
    prebuild_arch_overlay = {}
    for x in arch:
        prebuild_arch_overlay[x] = {}
        for y in ['files', 'dirs']:
            prebuild_overlay[y] = []
            prebuild_arch_overlay[x][y] = []
    for path, dirs, files in os.walk('{0}/pre-build.d/'.format(extradir)):
        prebuild_overlay['dirs'].append('{0}/'.format(path))
        for file in files:
            prebuild_overlay['files'].append(os.path.join(path, file))
    for x in prebuild_overlay.keys():
        prebuild_overlay[x][:] = [re.sub('^{0}/pre-build.d/'.format(extradir), '', s) for s in prebuild_overlay[x]]
        prebuild_overlay[x] = list(filter(None, prebuild_overlay[x]))
        for y in prebuild_arch_overlay.keys():
            prebuild_arch_overlay[y][x][:] = [i for i in prebuild_overlay[x] if i.startswith(y)]
            prebuild_arch_overlay[y][x][:] = [re.sub('^{0}/'.format(y), '', s) for s in prebuild_arch_overlay[y][x]]
            prebuild_arch_overlay[y][x] = list(filter(None, prebuild_arch_overlay[y][x]))
        prebuild_overlay[x][:] = [y for y in prebuild_overlay[x] if not y.startswith(('x86_64','i686'))]
    prebuild_overlay['dirs'].remove('/')
    # create the dir structure. these should almost definitely be owned by root.
    for a in arch:
        for dir in prebuild_overlay['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        # and copy over the files. again, chown to root.
        for file in prebuild_overlay['files']:
            shutil.copy2('{0}/pre-build.d/{1}'.format(extradir, file),
                        '{0}/root.{1}/{2}'.format(chrootdir, a, file), follow_symlinks = False)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
        # do the same for arch-specific stuff.
        for dir in prebuild_arch_overlay[a]['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        for file in prebuild_arch_overlay[a]['files']:
            shutil.copy2('{0}/pre-build.d/{1}/{2}'.format(extradir, a, file),
                        '{0}/root.{1}/{2}'.format(chrootdir, a, file), follow_symlinks = False)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)

def prepChroot(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    user = conf['user']
    chrootdir = build['chrootdir']
    prepdir = build['prepdir']
    arch = build['arch']
    bdisk_repo_dir = build['basedir']
    dlpath = build['dlpath']
    templates_dir = bdisk_repo_dir + '/extra/templates'
    #build = {}  # why was this here?
    ## let's prep some variables to write out the version info.txt
    # and these should be passed in from the args, from the most part.
    build['name'] = bdisk['name']
    build['time'] = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")
    hostname = host.getHostname
    build['user'] = os.environ['USER']
    if 'SUDO_USER' in os.environ:
        build['realuser'] = os.environ['SUDO_USER']
    build['buildnum'] += 1
    with open(dlpath + '/buildnum', 'w+') as f:
        f.write(str(build['buildnum']) + "\n")
    # and now that we have that dict, let's write out the VERSION_INFO.txt file.
    loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = loader)
    tpl = env.get_template('VERSION_INFO.txt.j2')
    tpl_out = tpl.render(build = build, bdisk = bdisk, hostname = host.getHostname(), distro = host.getOS())
    for a in arch:
        # Copy the GPG pubkey
        shutil.copy2('{0}/gpgkey.pub'.format(dlpath), '{0}/root.{1}/root/pubkey.gpg'.format(chrootdir, a))
        # Write the VERSION_INFO.txt from template
        with open('{0}/root.{1}/root/VERSION_INFO.txt'.format(chrootdir, a), 'w+') as f:
            f.write(tpl_out)
        with open('{0}/VERSION_INFO.txt'.format(prepdir), 'w+') as f:
            f.write(tpl_out)
    # And perform the templating overlays
    templates_overlay = {}
    templates_arch_overlay = {}
    for x in arch:
        templates_arch_overlay[x] = {}
        for y in ['files', 'dirs']:
            templates_overlay[y] = []
            templates_arch_overlay[x][y] = []
    for path, dirs, files in os.walk('{0}/pre-build.d'.format(templates_dir)):
        for dir in dirs:
            templates_overlay['dirs'].append('{0}/'.format(dir))
        for file in files:
            templates_overlay['files'].append(os.path.join(path, file))
    for x in templates_overlay.keys():
        templates_overlay[x][:] = [re.sub('^{0}/pre-build.d/(.*)(\.j2)'.format(templates_dir), '\g<1>', s) for s in templates_overlay[x]]
        templates_overlay[x] = list(filter(None, templates_overlay[x]))
        for y in templates_arch_overlay.keys():
            templates_arch_overlay[y][x][:] = [i for i in templates_overlay[x] if i.startswith(y)]
            templates_arch_overlay[y][x][:] = [re.sub('^{0}/(.*)(\.j2)'.format(y), '\g<1>', s) for s in templates_arch_overlay[y][x]]
            templates_arch_overlay[y][x][:] = [re.sub('^{0}/'.format(y), '', s) for s in templates_arch_overlay[y][x]]
            templates_arch_overlay[y][x] = list(filter(None, templates_arch_overlay[y][x]))
        templates_overlay[x][:] = [y for y in templates_overlay[x] if not y.startswith(('x86_64','i686'))]
    if '/' in templates_overlay['dirs']:
        templates_overlay['dirs'].remove('/')
    # create the dir structure. these should almost definitely be owned by root.
    if build['gpg']:
        gpg = conf['gpgobj']
        if conf['gpg']['mygpgkey']:
            signkey = conf['gpg']['mygpgkey']
        else:
            signkey = str(gpg.signers[0].subkeys[0].fpr)
    for a in arch:
        for dir in templates_overlay['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        # and write the files. again, chown to root.
        for file in templates_overlay['files']:
            tplname = 'pre-build.d/{0}.j2'.format(file)
            tpl = env.get_template(tplname)
            tpl_out = tpl.render(build = build, bdisk = bdisk, mygpgkey = signkey, user = user)
            with open('{0}/root.{1}/{2}'.format(chrootdir, a, file), 'w') as f:
                f.write(tpl_out)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
        # do the same for arch-specific stuff.
        for dir in templates_arch_overlay[a]['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        for file in templates_arch_overlay[a]['files']:
            tplname = 'pre-build.d/{0}/{1}.j2'.format(a, file)
            tpl = env.get_template('{0}'.format(tplname))
            tpl_out = tpl.render(build = build, bdisk = bdisk, mygpgkey = signkey)
            with open('{0}/root.{1}/{2}'.format(chrootdir, a, file), 'w') as f:
                f.write(tpl_out)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
    return(build)

def postChroot(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    dlpath = build['dlpath']
    chrootdir = build['chrootdir']
    arch = build['arch']
    overdir = build['basedir'] + '/overlay/'
    templates_dir = '{0}/extra/templates'.format(build['basedir'])
    loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = loader)
    postbuild_overlay = {}
    postbuild_arch_overlay = {}
    for x in arch:
        os.remove('{0}/root.{1}/README'.format(chrootdir, x))
        postbuild_arch_overlay[x] = {}
        for y in ['files', 'dirs']:
            postbuild_overlay[y] = []
            postbuild_arch_overlay[x][y] = []
    for path, dirs, files in os.walk(overdir):
        postbuild_overlay['dirs'].append('{0}/'.format(path))
        for file in files:
            postbuild_overlay['files'].append(os.path.join(path, file))
    for x in postbuild_overlay.keys():
        postbuild_overlay[x][:] = [re.sub('^' + overdir, '', s) for s in postbuild_overlay[x]]
        postbuild_overlay[x] = list(filter(None, postbuild_overlay[x]))
        for y in postbuild_arch_overlay.keys():
            postbuild_arch_overlay[y][x][:] = [i for i in postbuild_overlay[x] if i.startswith(y)]
            postbuild_arch_overlay[y][x][:] = [re.sub('^' + y + '/', '', s) for s in postbuild_arch_overlay[y][x]]
            postbuild_arch_overlay[y][x] = list(filter(None, postbuild_arch_overlay[y][x]))
        postbuild_overlay[x][:] = [y for y in postbuild_overlay[x] if not y.startswith(('x86_64','i686'))]
    postbuild_overlay['dirs'].remove('/')
    # create the dir structure. these should almost definitely be owned by root.
    for a in arch:
        for dir in postbuild_overlay['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0, follow_symlinks = False)
        # and copy over the files. again, chown to root.
        for file in postbuild_overlay['files']:
            shutil.copy2(overdir + file, '{0}/root.{1}/{2}'.format(chrootdir, a, file), follow_symlinks = False)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
        # do the same for arch-specific stuff.
        for dir in postbuild_arch_overlay[a]['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0, follow_symlinks = False)
        for file in postbuild_arch_overlay[a]['files']:
            shutil.copy2('{0}{1}/{2}'.format(overdir, a, file),
                            '{0}/root.{1}/{2}'.format(chrootdir, a, file),
                            follow_symlinks = False)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
    # And perform the templating overlays
    templates_overlay = {}
    templates_arch_overlay = {}
    for x in arch:
        templates_arch_overlay[x] = {}
        for y in ['files', 'dirs']:
            templates_overlay[y] = []
            templates_arch_overlay[x][y] = []
    for path, dirs, files in os.walk('{0}/overlay'.format(templates_dir)):
        for dir in dirs:
            templates_overlay['dirs'].append('{0}/'.format(dir))
        for file in files:
            templates_overlay['files'].append(os.path.join(path, file))
    for x in templates_overlay.keys():
        templates_overlay[x][:] = [re.sub('^{0}/overlay/(.*)(\.j2)'.format(templates_dir), '\g<1>', s) for s in templates_overlay[x]]
        templates_overlay[x] = list(filter(None, templates_overlay[x]))
        for y in templates_arch_overlay.keys():
            templates_arch_overlay[y][x][:] = [i for i in templates_overlay[x] if i.startswith(y)]
            templates_arch_overlay[y][x][:] = [re.sub('^{0}/(.*)(\.j2)'.format(y), '\g<1>', s) for s in templates_arch_overlay[y][x]]
            templates_arch_overlay[y][x][:] = [re.sub('^{0}/'.format(y), '', s) for s in templates_arch_overlay[y][x]]
            templates_arch_overlay[y][x] = list(filter(None, templates_arch_overlay[y][x]))
        templates_overlay[x][:] = [y for y in templates_overlay[x] if not y.startswith(('x86_64','i686'))]
    if '/' in templates_overlay['dirs']:
        templates_overlay['dirs'].remove('/')
    # create the dir structure. these should almost definitely be owned by root.
    if build['gpg']:
        gpg = conf['gpgobj']
        if conf['gpg']['mygpgkey']:
            signkey = conf['gpg']['mygpgkey']
        else:
            signkey = str(gpg.signers[0].subkeys[0].fpr)
    for a in arch:
        for dir in templates_overlay['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        # and write the files. again, chown to root.
        for file in templates_overlay['files']:
            tplname = 'overlay/{0}.j2'.format(file)
            tpl = env.get_template(tplname)
            tpl_out = tpl.render(build = build, bdisk = bdisk, mygpgkey = signkey)
            with open('{0}/root.{1}/{2}'.format(chrootdir, a, file), 'w') as f:
                f.write(tpl_out)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
        # do the same for arch-specific stuff.
        for dir in templates_arch_overlay[a]['dirs']:
            os.makedirs('{0}/root.{1}/{2}'.format(chrootdir, a, dir), exist_ok = True)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, dir), 0, 0)
        for file in templates_arch_overlay[a]['files']:
            tplname = 'overlay/{0}/{1}.j2'.format(a, file)
            tpl = env.get_template(tplname)
            tpl_out = tpl.render(build = build, bdisk = bdisk, mygpgkey = signkey)
            with open('{0}/root.{1}/{2}'.format(chrootdir, a, file), 'w') as f:
                f.write(tpl_out)
            os.chown('{0}/root.{1}/{2}'.format(chrootdir, a, file), 0, 0, follow_symlinks = False)
