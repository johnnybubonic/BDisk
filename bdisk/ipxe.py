import os
import shutil
import re
import subprocess
import jinja2
import git
import patch
import datetime
import humanize
import hashlib


def buildIPXE(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    mini = ipxe['iso']
    usb = ipxe['usb']
    tempdir = conf['build']['tempdir']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    patches_dir = tempdir + '/patches'
    srcdir = build['srcdir']
    embedscript = build['dlpath'] + '/EMBED'
    ipxe_src = srcdir + '/ipxe'
    img_path = build['isodir'] + '/'
    ipxe_usb = '{0}-{1}-{2}.usb.img'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    ipxe_mini = '{0}-{1}-{2}.mini.iso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    ipxe_emini = '{0}-{1}-{2}.mini.eiso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    usb_file = '{0}{1}'.format(img_path, ipxe_usb)
    emini_file = '{0}{1}'.format(img_path, ipxe_emini)
    mini_file = '{0}{1}'.format(img_path, ipxe_mini)
    ipxe_git_uri = 'git://git.ipxe.org/ipxe.git'
    patches_git_uri = 'https://github.com/eworm-de/ipxe.git'
    print('{0}: [IPXE] Prep/fetch sources...'.format(
                                        datetime.datetime.now()))
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
    # TODO: per http://ipxe.org/download#uefi, it builds efi *binaries* now.
    # we can probably skip the commit patching from eworm and the iso/eiso
    # (and even usb) generation, and instead use the same method we use in genISO
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
        generalconf = f.read()
    # And in config/console.h
    with open('{0}/src/config/console.h'.format(ipxe_src), 'r') as f:
        consoleconf = f.read()
    patterns = (('^#undef(\s*NET_PROTO_IPV6.*)$','#define\g<1>'),  # enable IPv6
                ('^#undef(\s*DOWNLOAD_PROTO_HTTPS)','#define\g<1>'),  # enable HTTPS
                ('^//(#define\s*IMAGE_TRUST_CMD)','\g<1>'),  # moar HTTPS
                ('^#undef(\s*DOWNLOAD_PROTO_FTP)','#define\g<1>'))  # enable FTP 
                #('^//(#define\s*CONSOLE_CMD)','\g<1>'),  # BROKEN in EFI? TODO. if enable, replace } with , above etc.
                #('^//(#define\s*IMAGE_PNG','\g<1>'),  # SAME, broken in EFI? TODO.
    #console = ('^//(#define\s*CONSOLE_VESAFB)','\g<1>')  # BROKEN in EFI? TODO.
    # https://stackoverflow.com/a/4427835
    # https://emilics.com/notebook/enblog/p869.html
    # The above methods don't seem to work. it craps out on the pattern matchings
    # so we use tuples instead.
    for x in patterns:
        generalconf = re.sub(x[0], x[1], generalconf, flags=re.MULTILINE)
    with open('{0}/src/config/general.h'.format(ipxe_src), 'w') as f:
        f.write(generalconf)
    # Uncomment when we want to test the above consdict etc.
    #for x in patterns:
    #    generalconf = re.sub(x[0], x[1], generalconf, flags=re.MULTILINE)
    #with open('{0}/src/config/console.h'.format(ipxe_src), 'w') as f:
    #    f.write(console)
    # Now we make!
    cwd = os.getcwd()
    os.chdir(ipxe_src + '/src')
    # TODO: split this into logic to only create the selected images.
    # Command to build the .efi file
    modenv = os.environ.copy()
    modenv['EMBED'] = embedscript
    #modenv['TRUST'] = ipxe_ssl_ca  # TODO: test these
    #modenv['CERT'] = '{0},{1}'.format(ipxe_ssl_ca, ipxe_ssl_crt)  # TODO: test these
    #modenv['PRIVKEY'] = ipxe_ssl_ckey  # TODO: test these
    build_cmd = {}
    # This build include the USB image.
    build_cmd['base'] = ['/usr/bin/make',
                            'all',
                            'EMBED={0}'.format(embedscript)]
    # TODO: copy the UNDI stuff/chainloader to tftpboot, if enabled
    build_cmd['undi'] = ['/usr/bin/make',
                            'bin/ipxe.pxe',
                            'EMBED={0}'.format(embedscript)]
    build_cmd['efi'] = ['/usr/bin/make',
                            'bin-i386-efi/ipxe.efi',
                            'bin-x86_64-efi/ipxe.efi',
                            'EMBED={0}'.format(embedscript)]
    # Command to build the actual mini image
    build_cmd['iso'] = ['/usr/bin/make',
                            'bin/ipxe.liso',
                            'bin/ipxe.eiso',
                            'EMBED={0}'.format(embedscript)]
    # Now we call the commands.
    DEVNULL = open(os.devnull, 'w')
    if os.path.isfile(build['dlpath'] + '/ipxe.log'):
        os.remove(build['dlpath'] + '/ipxe.log')
    print(('{0}: [IPXE] Building iPXE ({1}). PROGRESS: tail -f {2}/ipxe.log ...').format(
                                            datetime.datetime.now(),
                                            ipxe_src,
                                            build['dlpath']))
    with open('{0}/ipxe.log'.format(build['dlpath']), 'a') as f:
        subprocess.call(build_cmd['base'], stdout = f, stderr = subprocess.STDOUT, env=modenv)
        subprocess.call(build_cmd['undi'], stdout = f, stderr = subprocess.STDOUT, env=modenv)
        subprocess.call(build_cmd['efi'], stdout = f, stderr = subprocess.STDOUT, env=modenv)
        if mini:
            subprocess.call(build_cmd['iso'], stdout = f, stderr = subprocess.STDOUT, env=modenv)
    print('{0}: [IPXE] Built iPXE image(s) successfully.'.format(datetime.datetime.now()))
    os.chdir(cwd)
    # move the files to the results dir
    # TODO: grab ipxe.pxe here too.
    if usb:
        os.rename('{0}/src/bin/ipxe.usb'.format(ipxe_src), usb_file)
    if mini:
        os.rename('{0}/src/bin/ipxe.eiso'.format(ipxe_src), emini_file)
        os.rename('{0}/src/bin/ipxe.iso'.format(ipxe_src), mini_file)
    # Get size etc. of build results
    iso = {}
    stream = {}
    iso['name'] = []
    for t in ('usb', 'mini'):  # TODO: do this programmatically based on config
        if t == 'usb':
            imgname = 'USB'
        elif t == 'mini':
            imgname = 'Mini'
        iso['name'].append(t)
        iso[t] = {}
        shasum = False
        shasum = hashlib.sha256()
        if t == 'usb':
            isopath = usb_file
        elif t == 'mini':
            isopath = mini_file
        stream = False
        if os.path.isfile(isopath):
            with open(isopath, 'rb') as f:
                while True:
                    stream = f.read(65536)  # 64kb chunks
                    if not stream:
                        break
                    shasum.update(stream)
            iso[t]['sha'] = shasum.hexdigest()
            iso[t]['file'] = isopath
            iso[t]['size'] = humanize.naturalsize(os.path.getsize(isopath))
            iso[t]['type'] = 'iPXE {0}'.format(imgname)
            if t == 'usb':
                iso[t]['fmt'] = 'Image'
            elif t == 'mini':
                iso[t]['fmt'] = 'ISO'
    return(iso)
