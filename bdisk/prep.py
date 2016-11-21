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

def archChk(arch):
    if arch in ['i686', 'x86_64']:
        return(arch)
    else:
        exit("{0} is not a valid architecture. Must be one of i686 or x86_64.".format(arch))

def dirChk(config_dict):
    # Make dirs if they don't exist
    for d in ('archboot', 'isodir', 'mountpt', 'srcdir', 'tempdir'):
        os.makedirs(config_dict['build'][d], exists_ok = True)
    # Make dirs for sync staging if we need to
    for x in ('http', 'tftp'):
        if config_dict['sync'][x]:
            os.makedirs(config_dict[x]['path'], exist_ok = True)

def downloadTarball(arch, dlpath):
    # arch - should be i686 or x86_64
    # returns path/filename e.g. /some/path/to/file.tar.gz
    # we use .gnupg since we'll need it later.
    archChk(arch)
    try:
        os.makedirs(dlpath + '/.gnupg')
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    tarball_path = dlpath + '/.latest.' + arch + '.tar.gz'
    #mirror = 'http://mirrors.kernel.org/archlinux'
    mirror = 'https://mirror.us.leaseweb.net/archlinux'
    rlsdir = mirror + '/iso/latest'
    sha_in = urlopen(rlsdir + '/sha1sums.txt')
    sha1sums = sha_in.read()
    sha_in.close()
    sha1_list = sha1sums.decode("utf-8")
    sha_list = list(filter(None, sha1_list.split('\n')))
    sha_dict = {x.split()[1]: x.split()[0] for x in sha_list}
    pattern = re.compile('^archlinux-bootstrap-[0-9]{4}\.[0-9]{2}\.[0-9]{2}-' + arch + '\.tar\.gz$')
    tarball = [filename.group(0) for l in list(sha_dict.keys()) for filename in [pattern.search(l)] if filename][0]
    sha1 = sha_dict[tarball]
    # all that lousy work just to get a sha1 sum. okay. so.
    if os.path.isfile(tarball_path):
        pass
    else:
        # fetch the tarball...
        print("Fetching the tarball for {0} architecture, please wait...".format(arch))
        tarball_dl = urlopen(rlsdir + tarball)
        with open(dlpath + '/latest.' + arch + '.tar.gz', 'wb') as f:
            f.write(tarball_dl)
        tarball_dl.close()
    tarball_hash = hashlib.sha1(open(tarball_path, 'rb').read()).hexdigest()
    if tarball_hash != sha1:
        exit("There was a failure fetching the tarball and the wrong version exists on the filesystem.\nPlease try again later.")
    else:
        # okay, so the sha1 matches. let's verify the signature.
        # we don't want to futz with the user's normal gpg.
        gpg = gnupg.GPG(gnupghome = dlpath + '/.gnupg')
        input_data = gpg.gen_key_input(name_email = 'tempuser@nodomain.tld', passphrase = 'placeholder_passphrase')
        key = gpg.gen_key(input_data)
        keyid = '7F2D434B9741E8AC'
        gpg.recv_keys('pgp.mit.edu', keyid)
        gpg_sig = tarball + '.sig'
        sig_dl = urlopen(rlsdir + gpg_sig)
        with open(tarball_path + '.sig', 'wb+') as f:
            f.write(sig_dl)
        sig_dl.close()
        sig = tarball_path + '.sig'
        tarball_data = open(tarball_path, 'rb')
        tarball_data_in = tarball_data.read()
        gpg_verify = gpg.verify_data(sig, tarball_data_in)
        tarball_data.close()
        if not gpg_verify:
            exit("There was a failure checking the signature of the release tarball. Please investigate.")
        os.remove(sig)

    return(tarball_path)

def unpackTarball(tarball_path, chrootdir):
    # Make the dir if it doesn't exist
    try:
        os.makedirs(chrootdir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    # Open and extract the tarball
    tar = tarfile.open(tarball_path, 'r:gz')
    tar.extractall(path = destdir)
    tar.close()
    return(True)

def buildChroot(arch, chrootdir, dlpath, extradir):
    unpack_me = unpackTarball(downloadTarball(archChk(arch), dlpath), chrootdir)
    if unpack_me:
        pass
    else:
        exit("Something went wrong when trying to unpack the tarball.")

    print("The download and extraction has completed. Now prepping the chroot environment with some additional changes.")
    # build dict of lists of files and dirs from pre-build.d dir, do the same with arch-specific changes.
    prebuild_overlay = {}
    prebuild_arch_overlay = {}
    for x in ['i686', 'x86_64']:
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
    for dir in prebuild_overlay['dirs']:
        os.makedirs(chrootdir + '/' + dir, exist_ok = True)
        os.chown(chrootdir + '/' + dir, 0, 0)
    # and copy over the files. again, chown to root.
    for file in prebuild_overlay['files']:
        shutil.copy2(extradir + '/pre-build.d/' + file, chrootdir + '/' + file)
        os.chown(chrootdir + '/' + file, 0, 0)
    # do the same for arch-specific stuff.
    for dir in prebuild_arch_overlay[arch]['dirs']:
        os.makedirs(chrootdir + '/' + dir, exist_ok = True)
        os.chown(chrootdir + '/' + dir, 0, 0)
    for file in prebuild_arch_overlay[arch]['files']:
        shutil.copy2(extradir + '/pre-build.d/' + arch + '/' + file, chrootdir + '/' + file)
        os.chown(chrootdir + '/' + file, 0, 0)
    return(chrootdir)

def prepChroot(templates_dir, chrootdir, bdisk, arch):
    build = {}
    # let's prep some variables to write out the version info.txt
    # get the git tag and short commit hash
    repo = git.Repo(bdisk['dir'])
    refs = repo.git.describe(repo.head.commit).split('-')
    build['ver'] = refs[0] + '-' + refs[2]
    # and these should be passed in from the args, from the most part.
    build['name'] = bdisk['name']
    build['time'] = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")
    build['host'] = bdisk['hostname']
    build['user'] = os.environ['USER']
    if os.environ['SUDO_USER']:
        build['realuser'] = os.environ['SUDO_USER']
    # and now that we have that dict, let's write out the VERSION_INFO.txt file.
    env = jinja2.Environment(loader=FileSystemLoader(templates_dir))
    tpl = env.get_template('VERSION_INFO.txt.j2')
    tpl_out = template.render(build = build)
    with open(chrootdir + '/root/VERSION_INFO.txt', "wb+") as f:
        fh.write(tpl_out)
    return(build)
