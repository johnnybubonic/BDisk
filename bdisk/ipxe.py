import os
import shutil
import re
import subprocess
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
    tempdir = conf['build']['tempdir']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    patches_dir = tempdir + '/patches'
    srcdir = build['srcdir']
    embedscript = tempdir + '/EMBED'
    ipxe_src = srcdir + '/ipxe'
    img_path = build['isodir'] + '/'
    ipxe_usb = '{0}-{1}.usb.img'.format(bdisk['uxname'], bdisk['ver'])
    ipxe_mini = '{0}-{1}.mini.iso'.format(bdisk['uxname'], bdisk['ver'])
    usb_file = '{0}/{1}'.format(img_path, ipxe_usb)
    mini_file = '{0}/{1}'.format(img_path, ipxe_mini)
    ipxe_git_uri = 'git://git.ipxe.org/ipxe.git'
    patches_git_uri = 'https://github.com/eworm-de/ipxe.git'
    print('{0}: Building iPXE in {1}. Please wait...'.format(
                                            datetime.datetime.now(),
                                            ipxe_src))
    # Get the source and apply some cherrypicks
    if os.path.isdir(ipxe_src):
        shutil.rmtree(ipxe_src)
    ipxe_repo = git.Repo.clone_from(ipxe_git_uri, ipxe_src)
    # Generate patches
    os.makedirs(patches_dir, exist_ok = True)
    os.makedirs(img_path, exist_ok = True)
    tpl_loader = jinja2.FileSystemLoader(ipxe_tpl)
    env = jinja2.Environment(loader = tpl_loader)
    patches = ipxe_repo.create_remote('eworm', patches_git_uri)
    patches.fetch()
    eiso_commit = '189652b03032305a2db860e76fb58e81e3420c4d'
    nopie_commit = '58557055e51b2587ad3843af58075de916e5399b'
    # patch files
    for p in ('01.git-version.patch', '02.banner.patch'):
        try:
            tpl = env.get_template('patches/{0}.j2'.format(p))
            tpl_out = tpl.render(bdisk = bdisk)
            with open('{0}/{1}'.format(patches_dir, p), 'w+') as f:
                f.write(tpl_out)
            patchfile = patch.fromfile(patches_dir + '/' + p)
            patchfile.apply(strip = 2, root = ipxe_src + '/src')
        except:
            pass
    tpl = env.get_template('EMBED.j2')
    tpl_out = tpl.render(ipxe = ipxe)
    with open(embedscript, 'w+') as f:
        f.write(tpl_out)
    # Patch using the files before applying the cherrypicks
    ipxe_repo.git.cherry_pick('-n', eiso_commit)
    ipxe_repo.git.cherry_pick('-n', nopie_commit)
    # Feature enabling
    # In config/general.h
    with open('{0}/src/config/general.h'.format(ipxe_src), 'r') as f:
        generalconf = f.readlines()
    # And in config/console.h
    with open('{0}/src/config/console.h'.format(ipxe_src), 'r') as f:
        consoleconf = f.readlines()
    gendict = {'^#undef(\s*NET_PROTO_IPV6)':'#define\g<1>',  # enable IPv6
                '^#undef(\s*DOWNLOAD_PROTO_HTTPS)':'#define\g<1>',  # enable HTTPS
                '^//(#define\s*IMAGE_TRUST_CMD)':'\g<1>',  # moar HTTPS
                '^#undef(\s*DOWNLOAD_PROTO_FTP)':'#define\g<1>'}  # FTP
                #'^//(#define\s*CONSOLE_CMD)':'\g<1>',  # BROKEN in EFI? TODO. if enable, replace } with , above etc.
                #'^//(#define\s*IMAGE_PNG':'\g<1>'}  # SAME, broken in EFI? TODO.
    consdict = {}#'^//(#define\s*CONSOLE_VESAFB)':'\g<1>'}  # BROKEN in EFI? TODO.
    # https://stackoverflow.com/a/4427835
    # https://emilics.com/notebook/enblog/p869.html
    sedlike = re.compile('|'.join(gendict.keys()))
    with open('{0}/src/config/general.h'.format(ipxe_src), 'w') as f:
        f.write(re.sub(lambda m: gendict[m.group(0)], generalconf))
    # Uncomment when we want to test the above consdict etc.
    #sedlike = re.compile('|'.join(consdict.keys()))
    #with open('{0}/src/config/console.h'.format(ipxe_src), 'w') as f:
    #    f.write(re.sub(lambda m: consdict[m.group(0)], consoleconf))
    # Now we make!
    cwd = os.getcwd()
    os.chdir(ipxe_src + '/src')
    # TODO: split this into logic to only create the selected images.
    # Command to build the .efi file
    build_efi = ['/usr/bin/make',
                'bin-i386-efi/ipxe.efi',
                'bin-x86_64-efi/ipxe.efi',
                'EMBED="{0}"'.format(embedscript)
                #'TRUST="{0}"'.format(ipxe_ssl_ca),  # finish work on ipxe SSL. make sure you throw a comma at the end above.
                #'CERT="{0},{1}"'.format(ipxe_ssl_ca, ipxe_ssl_crt),  # finish work on ipxe SSL
                #'PRIVKEY="{0}"'.format(ipxe_ssl_ckey)
                ]
    # Command to build the actual USB and Mini images
    build_boots = ['/usr/bin/make',
                'bin/ipxe.eiso',
                'bin/ipxe.usb',
                'EMBED="{0}"'.format(embedscript)
                #'TRUST="{0}"'.format(ipxe_ssl_ca),  # finish work on ipxe SSL. make sure you throw a comma at the end above.
                #'CERT="{0},{1}"'.format(ipxe_ssl_ca, ipxe_ssl_crt),  # finish work on ipxe SSL
                #'PRIVKEY="{0}"'.format(ipxe_ssl_ckey)
                ]
    # Now we call the commands.
    for n in ('build_efi', 'build_boots'):
        subprocess.call(n, stdout = DEVNULL, stderr = subprocess.STDOUT)  # TODO: log the make output to a file?
    os.chdir(cwd)
    # move the files to the results dir
    os.rename('{0}/src/bin/ipxe.usb'.format(ipxe_src), usb_file)
    os.rename('{0}/src/bin/ipxe.eiso'.format(ipxe_src), mini_file)
    # Get size etc. of build results
    iso = {}
    iso['name'] = []
    for t in ('USB', 'Mini'):  # TODO: do this programmatically based on config
        iso['name'].append(t)
        iso[t]['sha'] = hashlib.sha256()
        if t == 'USB':
            isopath = usb_file
        elif t == 'Mini':
            isopath = mini_file
        with open(isopath, 'rb') as f:
            while True:
                stream = f.read(65536)  # 64kb chunks
                if not stream:
                    break
            iso[t]['sha'].update(stream)
        iso[t]['sha'] = iso['sha'].hexdigest()
        iso[t]['file'] = isopath
        iso[t]['size'] = humanize.naturalsize(os.path.getsize(isopath))
        iso[t]['type'] = 'iPXE {0}'.format(t)
        if t == 'USB':
            iso[t]['fmt'] = 'Image'
        elif t == 'Mini':
            iso[t]['fmt'] = 'ISO'
    return(iso)
