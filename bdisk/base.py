#!/usr/bin/env python3

import os
import re
import hashlib
import gnupg
from urllib.request import urlopen

def download_tarball(arch, dlpath):
    # arch - should be i686 or x86_64
    # returns path/filename e.g. /some/path/to/file.tar.gz
    # we use .gnupg since we'll need it later.
    try:
        os.makedirs(dlpath + '/.gnupg')
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
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
    if os.path.isfile(dlpath + '/latest.' + arch + '.tar.gz'):
        pass
    else:
        # fetch the tarball...
        print("Fetching the tarball for {0} architecture, please wait...".format(arch))
        tarball_dl = urlopen(rlsdir + tarball)
        with open(dlpath + '/latest.' + arch + '.tar.gz', 'wb') as f:
            f.write(tarball_dl)
        tarball_dl.close()
    tarball_hash = hashlib.sha1(open(dlpath + '/latest.' + arch + '.tar.gz', 'rb').read()).hexdigest()
    if tarball_hash != sha1:
        exit("There was a failure fetching the tarball and the wrong version exists on the filesystem.\nPlease try again later.")
    else:
        # okay, so the sha1 matches. let's verify the signature.
        # we don't want to futz with the users normal gpg.
        gpg = gnupg.GPG(gnupghome=dlpath + '/.gnupg')
        input_data = gpg.gen_key_input(name_email='tempuser@nodomain.tld',passphrase='placeholder_passphrase')
        key = gpg.gen_key(input_data)
        keyid = '7F2D434B9741E8AC'
        gpg_sig = tarball + '.sig'
        sig_dl = urlopen(rlsdir + gpg_sig)
        with open(dlpath + '/latest.' + arch + '.tar.gz.sig', 'wb') as f:
            f.write(sig_dl)
        sig_dl.close()
        sig = dlpath + '/latest.' + arch + '.tar.gz.sig'
        gpg.verify_file(dlpath + '/latest.' + arch + '.tar.gz', sig_file = sig)


    return(sha1sum)

print(download_tarball('x86_64'))
