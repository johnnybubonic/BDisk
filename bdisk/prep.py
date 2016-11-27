import os
import shutil
import re
import hashlib
import gnupg
import tarfile
import subprocess
import re
import git
import jinja2
import datetime
from urllib.request import urlopen
import host  # bdisk.host

def dirChk(config_dict):
    # Make dirs if they don't exist
    for d in ('archboot', 'isodir', 'mountpt', 'srcdir', 'tempdir'):
        os.makedirs(config_dict['build'][d], exist_ok = True)
    # Make dirs for sync staging if we need to
    for x in ('http', 'tftp'):
        if config_dict['sync'][x]:
            os.makedirs(config_dict[x]['path'], exist_ok = True)

def downloadTarball(build):
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
    if build['mirrorgpgsig'] != '':
        # we don't want to futz with the user's normal gpg.
        gpg = gnupg.GPG(gnupghome = dlpath + '/.gnupg')
        print("\nNow generating a GPG key. Please wait...")
        # python-gnupg 0.3.9 spits this error in Arch. it's harmless, but ugly af.
        # TODO: remove this when the error doesn't happen anymore.
        print("If you see a \"ValueError: Unknown status message: 'KEY_CONSIDERED'\" error, it can be safely ignored.")
        print("If this is taking a VERY LONG time, try installing haveged and starting it. This can be " +
                        "done safely in parallel with the build process.\n")
        input_data = gpg.gen_key_input(name_email = 'tempuser@nodomain.tld', passphrase = 'placeholder_passphrase')
        key = gpg.gen_key(input_data)
        keyid = build['gpgkey']
        gpg.recv_keys(build['gpgkeyserver'], keyid)
    for a in arch:
        pattern = re.compile('^.*' + a + '\.tar(\.(gz|bz2|xz))?$')
        tarball = [filename.group(0) for l in list(sha_dict.keys()) for filename in [pattern.search(l)] if filename][0]
        sha1 = sha_dict[tarball]
        if os.path.isfile(tarball_path[a]):
            pass
        else:
            # fetch the tarball...
            print("Fetching the tarball for {0} architecture, please wait...".format(a))
            #dl_file = urllib.URLopener()
            tarball_dl = urlopen(rlsdir + tarball)
            with open(tarball_path[a], 'wb') as f:
                f.write(tarball_dl.read())
            tarball_dl.close()
        print(("Checking that the hash checksum for {0} matches {1}, please wait...").format(
                                tarball_path[a], sha1))
        tarball_hash = hashlib.sha1(open(tarball_path[a], 'rb').read()).hexdigest()
        if tarball_hash != sha1:
            exit(("There was a failure fetching {0} and the wrong version exists on the filesystem.\n" +
                                "Please try again later.").format(tarball))
        elif build['mirrorgpgsig'] != '':
            # okay, so the sha1 matches. let's verify the signature.
            if build['mirrorgpgsig'] == '.sig':
                gpgsig_remote = rlsdir + tarball + '.sig'
            else:
                gpgsig_remote = mirror + build['mirrorgpgsig']
            gpg_sig = tarball + '.sig'
            sig_dl = urlopen(gpgsig_remote)
            sig = tarball_path[a] + '.sig'
            with open(sig, 'wb+') as f:
                f.write(sig_dl.read())
            sig_dl.close()
            tarball_data = open(tarball_path[a], 'rb')
            tarball_data_in = tarball_data.read()
            gpg_verify = gpg.verify_data(sig, tarball_data_in)
            tarball_data.close()
            if not gpg_verify:
                exit("There was a failure checking {0} against {1}. Please investigate.".format(
                                 sig, tarball_path[a]))
            os.remove(sig)

    return(tarball_path)

def unpackTarball(tarball_path, build):
    chrootdir = build['chrootdir']
    # Make the dir if it doesn't exist
    shutil.rmtree(chrootdir, ignore_errors = True)
    os.makedirs(chrootdir, exist_ok = True)
    print("Now extracting the tarball(s). Please wait...")
    # Open and extract the tarball
    for a in build['arch']:
        tar = tarfile.open(tarball_path[a], 'r:gz')
        tar.extractall(path = chrootdir)
        tar.close()
        print("Extraction for {0} finished.".format(tarball_path[a]))

def buildChroot(build):
    dlpath = build['dlpath']
    chrootdir = build['chrootdir']
    arch = build['arch']
    extradir = build['basedir'] + '/extra'
    unpack_me = unpackTarball(downloadTarball(build), build)
    # build dict of lists of files and dirs from pre-build.d dir, do the same with arch-specific changes.
    prebuild_overlay = {}
    prebuild_arch_overlay = {}
    for x in arch:
        prebuild_arch_overlay[x] = {}
        for y in ['files', 'dirs']:
            prebuild_overlay[y] = []
            prebuild_arch_overlay[x][y] = []
    for path, dirs, files in os.walk(extradir + '/pre-build.d/'):
        prebuild_overlay['dirs'].append(path + '/')
        for file in files:
            prebuild_overlay['files'].append(os.path.join(path, file))
    for x in prebuild_overlay.keys():
        prebuild_overlay[x][:] = [re.sub('^' + extradir + '/pre-build.d/', '', s) for s in prebuild_overlay[x]]
        prebuild_overlay[x] = list(filter(None, prebuild_overlay[x]))
        for y in prebuild_arch_overlay.keys():
            prebuild_arch_overlay[y][x][:] = [i for i in prebuild_overlay[x] if i.startswith(y)]
            prebuild_arch_overlay[y][x][:] = [re.sub('^' + y + '/', '', s) for s in prebuild_arch_overlay[y][x]]
            prebuild_arch_overlay[y][x] = list(filter(None, prebuild_arch_overlay[y][x]))
        prebuild_overlay[x][:] = [y for y in prebuild_overlay[x] if not y.startswith(('x86_64','i686'))]
    prebuild_overlay['dirs'].remove('/')
    # create the dir structure. these should almost definitely be owned by root.
    for a in arch:
        for dir in prebuild_overlay['dirs']:
            os.makedirs(chrootdir + '/root.' + a + '/' + dir, exist_ok = True)
            os.chown(chrootdir + '/root.' + a + '/' + dir, 0, 0)
        # and copy over the files. again, chown to root.
        for file in prebuild_overlay['files']:
            shutil.copy2(extradir + '/pre-build.d/' + file, chrootdir + '/root.' + a + '/' + file)
            os.chown(chrootdir + '/root.' + a + '/' + file, 0, 0)
        # do the same for arch-specific stuff.
        for dir in prebuild_arch_overlay[a]['dirs']:
            os.makedirs(chrootdir + '/root.' + a + '/' + dir, exist_ok = True)
            os.chown(chrootdir + '/root.' + a + '/' + dir, 0, 0)
        for file in prebuild_arch_overlay[a]['files']:
            shutil.copy2(extradir + '/pre-build.d/' + a + '/' + file, chrootdir + '/root.' + a + '/' + file)
            os.chown(chrootdir + '/root.' + a + '/' + file, 0, 0)

def prepChroot(templates_dir, build, bdisk):
    chrootdir = build['chrootdir']
    arch = build['arch']
    bdisk_repo_dir = build['basedir']
    build = {}
    # let's prep some variables to write out the version info.txt
    # get the git tag and short commit hash
    repo = git.Repo(bdisk_repo_dir)
    refs = repo.git.describe(repo.head.commit).split('-')
    build['ver'] = refs[0] + '-' + refs[2]
    # and these should be passed in from the args, from the most part.
    build['name'] = bdisk['name']
    build['time'] = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")
    hostname = host.getHostname
    build['user'] = os.environ['USER']
    if 'SUDO_USER' in os.environ:
        build['realuser'] = os.environ['SUDO_USER']
    # and now that we have that dict, let's write out the VERSION_INFO.txt file.
    loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = loader)
    tpl = env.get_template('VERSION_INFO.txt.j2')
    tpl_out = tpl.render(build = build, hostname = hostname)
    for a in arch:
        with open(chrootdir + '/root.' + a + '/root/VERSION_INFO.txt', "w+") as f:
            f.write(tpl_out)
    return(build)
