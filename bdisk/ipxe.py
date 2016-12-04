import os
import shutil
import jinja2
import git
import patch
import datetime
import bSSL


def sslIPXE(conf):
    try:
        ca = conf['ipxe']['ssl_ca']
    except:
        ca = None
    try:
        cakey = conf['ipxe']['ssl_cakey']
    except:
        cakey = None
    try:
        crt = conf['ipxe']['ssl_crt']
    except:
        crt = None
    try:
        key = conf['ipxe']['ssl_key']
    except:
        key = None
    # http://www.pyopenssl.org/en/stable/api/crypto.html#pkey-objects
    # http://docs.ganeti.org/ganeti/2.14/html/design-x509-ca.html
    if not cakey:
        cakey = bSSL.sslCAKey

    pass

def buildIPXE(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    patches_dir = ipxe_tpl + '/patches'
    srcdir = build['srcdir']
    ipxe_src = srcdir + '/ipxe'
    ipxe_git_uri = 'git://git.ipxe.org/ipxe.git'
    patches_git_uri = 'https://github.com/eworm-de/ipxe.git'
    print('{0}: Building iPXE in {1}. Please wait...'.format(
                                            datetime.datetime.now(),
                                            ipxe_src))
    # Get the source and apply some cherrypicks
    if os.path.isdir(ipxe_src):
        shutil.rmtree(ipxe_src)
    ipxe_repo = git.Repo.clone_from(ipxe_git_uri, ipxe_src)
    patches = ipxe_repo.create_remote('eworm', patches_git_uri)
    patches.fetch()
    eiso_commit = '189652b03032305a2db860e76fb58e81e3420c4d'
    nopie_commit = '58557055e51b2587ad3843af58075de916e5399b'
    # patch files
    for p in ('01.git-version.patch.j2', '02.banner.patch.j2'):
        try:
            patchfile = patch.fromfile(patches_dir + '/' + p)
            patchfile.apply(strip = 2, root = ipxe_src + '/src')
        except:
            pass
    # Patch using the files before applying the cherrypicks
    ipxe_repo.git.cherry_pick('-n', eiso_commit)
    ipxe_repo.git.cherry_pick('-n', nopie_commit)
    # Now we make!
    cwd = os.getcwd()
    os.chdir(ipxe_src + '/src')

    os.chdir(cwd)
