#!/usr/bin/env python3

import os
import re
import hashlib
import gnupg
import tarfile
from urllib.request import urlopen

def arch_chk(arch):
    if arch in ['i686', 'x86_64']:
        return(arch)
    else:
        exit("{0} is not a valid architecture. Must be one of i686 or x86_64.".format(arch))

def download_tarball(arch, dlpath):
    # arch - should be i686 or x86_64
    # returns path/filename e.g. /some/path/to/file.tar.gz
    # we use .gnupg since we'll need it later.
    arch_chk(arch)
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

def unpack_tarball(tarball_path, destdir):
    # Make the dir if it doesn't exist
    try:
        os.makedirs(destdir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    # Open and extract the tarball
    tar = tarfile.open(tarball_path, 'r:gz')
    tar.extractall(path = destdir)
    tar.close()
    return(True)

def build_chroot(arch, destdir, dlpath):
    unpack_me = unpack_tarball(download_tarball(arch_chk(arch), dlpath), destdir)
    if unpack_me:
        pass
    else:
        exit("Something went wrong when trying to unpack the tarball.")
    return(destdir)
