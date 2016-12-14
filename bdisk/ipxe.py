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
    tempdir = conf['build']['tempdir']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    patches_dir = tempdir + '/patches'
    srcdir = build['srcdir']
    embedscript = build['dlpath'] + '/EMBED'
    ipxe_src = srcdir + '/ipxe'
    ipxe_git_uri = 'git://git.ipxe.org/ipxe.git'
    #patches_git_uri = 'https://github.com/eworm-de/ipxe.git'  # DO WE EVEN NEED THIS ANYMORE THO
    print('{0}: [IPXE] Prep/fetch sources...'.format(
                                        datetime.datetime.now()))
    # Get the source and apply some cherrypicks
    if os.path.isdir(ipxe_src):
        shutil.rmtree(ipxe_src)
    ipxe_repo = git.Repo.clone_from(ipxe_git_uri, ipxe_src)
    # Generate patches
    #os.makedirs(patches_dir, exist_ok = True)  # needed?
    os.makedirs(img_path, exist_ok = True)
    tpl_loader = jinja2.FileSystemLoader(ipxe_tpl)
    env = jinja2.Environment(loader = tpl_loader)
    #patches = ipxe_repo.create_remote('eworm', patches_git_uri)  # needed?
    #patches.fetch()  # needed?
    # TODO: per http://ipxe.org/download#uefi, it builds efi *binaries* now.
    # we can probably skip the commit patching from eworm and the iso/eiso
    # (and even usb) generation, and instead use the same method we use in genISO
    #eiso_commit = '189652b03032305a2db860e76fb58e81e3420c4d'  # needed?
    #nopie_commit = '58557055e51b2587ad3843af58075de916e5399b'  # needed?
    # patch files needed?
   # for p in ('01.git-version.patch', '02.banner.patch'):
   #     try:
   #         tpl = env.get_template('patches/{0}.j2'.format(p))
   #         tpl_out = tpl.render(bdisk = bdisk)
   #         with open('{0}/{1}'.format(patches_dir, p), 'w+') as f:
   #             f.write(tpl_out)
   #         patchfile = patch.fromfile(patches_dir + '/' + p)
   #         patchfile.apply(strip = 2, root = ipxe_src + '/src')
   #     except:
   #         pass
    tpl = env.get_template('EMBED.j2')
    tpl_out = tpl.render(ipxe = ipxe)
    with open(embedscript, 'w+') as f:
        f.write(tpl_out)
    # Patch using the files before applying the cherrypicks needed?
   # ipxe_repo.git.cherry_pick('-n', eiso_commit)
   # ipxe_repo.git.cherry_pick('-n', nopie_commit)
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
    # Command to build the actual mini image needed?
   # build_cmd['iso'] = ['/usr/bin/make',
   #                         'bin/ipxe.liso',
   #                         'bin/ipxe.eiso',
   #                         'EMBED={0}'.format(embedscript)]
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
        #if mini:
        #    subprocess.call(build_cmd['iso'], stdout = f, stderr = subprocess.STDOUT, env=modenv)
    print('{0}: [IPXE] Built iPXE image(s) successfully.'.format(datetime.datetime.now()))
    os.chdir(cwd)
    # move the files to the results dir
    # TODO: grab ipxe.pxe here too.
   # if mini: # needed?
   #     os.rename('{0}/src/bin/ipxe.eiso'.format(ipxe_src), emini_file)
   #     os.rename('{0}/src/bin/ipxe.iso'.format(ipxe_src), mini_file)
    # Get size etc. of build results
    iso = {}
    stream = {}
    iso['name'] = []
    for t in ('usb'):  # TODO: do this programmatically based on config
        if t == 'usb':
            imgname = 'USB'
        iso['name'].append(t)
        iso[t] = {}
        shasum = False
        shasum = hashlib.sha256()
        if t == 'mini':
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

def genISO(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    arch = build['arch']
    ver = build['ver']
    isofile = '{0}-{1}-{2}.mini.iso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    isopath = '{0}/{1}'.format(isodir, isofile)
    tempdir = build['tempdir']
    chrootdir = build['chrootdir']
    mini = ipxe['iso']
    iso = {}
    srcdir = build['srcdir']
    ipxe_src = srcdir + '/ipxe'
    mountpt = build['mountpt']
    templates_dir = build['basedir'] + '/extra/templates/iPXE/'
    tpl_loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = tpl_loader)
    bootdir = tempdir + '/ipxe_mini'
    efiboot_img = bootdir + '/efiboot.efi'
    innerefi64 = '{0}/src/bin-x86_64-efi/ipxe.efi'.format(ipxe_src)
    efi = False
    # this shouldn't be necessary... if it is, we can revisit this in the future. see "Inner dir" below.
    #innerefi32 = '{0}/src/bin-i386-efi/ipxe.efi'.format(ipxe_src)
    # We only need to do EFI prep if we have UEFI/x86_64 support. See above, but IA64 is dead, Zed.
    if mini and (('x86_64') in arch):
        efi = True
        # EFI prep/building
        print('{0}: [IPXE] UEFI support for Mini ISO...'.format(datetime.datetime.now()))
        if os.path.isdir(bootdir):
            shutil.rmtree(bootdir)
        # Inner dir (efiboot.img file)
        sizetotal = 65536  # 64K wiggle room. increase this if we add IA64.
        sizetotal += os.path.getsize(innerefi64)
        print("{0}: [IPXE] Creating EFI ESP image {1} ({2})...".format(
                                                                datetime.datetime.now(),
                                                                efiboot_img,
                                                                humanize.naturalsize(sizetotal)))
        if os.path.isfile(efiboot_img):
            os.remove(efiboot_img)
        with open(efiboot_img, 'wb+') as f:
            f.truncate(sizetotal)
        DEVNULL = open(os.devnull, 'w')
        cmd = ['/sbin/mkfs.vfat', '-F', '32', '-n', 'iPXE_EFI', efiboot_img]
        subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        cmd = ['/bin/mount', efiboot_img, build['mountpt']]
        subprocess.call(cmd)
        os.makedirs(mountpt + '/EFI/BOOT')
        shutil.copy2(innerefi64,'{0}/EFI/BOOT/BOOTX64.EFI'.format(mountpt))
        cmd = ['/bin/umount', mountpt]
        subprocess.call(cmd)
        # Outer dir
        os.makedirs('{0}/boot'.format(bootdir), exist_ok = True)  # kernel(s)
        os.makedirs('{0}/EFI/BOOT'.format(bootdir), exist_ok = True)  # EFI
        os.makedirs('{0}/loader/entries'.format(bootdir), exist_ok = True)  # EFI
        os.makedirs('{0}/isolinux'.format(bootdir), exist_ok = True)  # BIOS
        # we reuse the preloader.efi from full ISO build
        shutil.copy2('{0}/EFI/boot/bootx64.efi'.format(tempdir),
                        '{0}/EFI/BOOT/BOOTX64.EFI'.format(bootdir))
        # and we create the loader entries
        for t in ('loader','base'):
            if t == 'base':
                name = bdisk['uxname']
                tplpath = '{0}/loader/entries'.format(bootdir)
            else:
                name = t
                tplpath = '{0}/loader'.format(bootdir)
            tpl = env.get_template('EFI/{0}.conf.j2'.format(t))
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            with open('{0}/{1}.conf'.format(tplpath, name), "w+") as f:
                f.write(tpl_out)
    if mini:
        # BIOS prepping
        shutil.copy2('{0}/src/bin/ipxe.lkrn'.format(ipxe_src), '{0}/boot/ipxe.krn'.format(bootdir))
        isolinux_filelst = ['isolinux.bin',
                            'ldlinux.c32']
        for f in isolinux_filelst:
            shutil.copy2('{0}/root.{1}/usr/lib/syslinux/bios/{2}'.format(chrootdir, arch[0], f), '{0}/{1}'.format(bootdir, f))
        tpl = env.get_template('BIOS/isolinux.cfg.j2')
        tpl_out = tpl.render(build = build, bdisk = bdisk)
        with open('{0}/isolinux.cfg'.format(bootdir), "w+") as f:
            f.write(tpl_out)
        print("{0}: [IPXE] Building Mini ISO ({1})...".format(datetime.datetime.now(), isopath))
        if efi:
            cmd = ['/usr/bin/xorriso',
                    '-as', 'mkisofs',
                    '-iso-level', '3',
                    '-full-iso9660-filenames',
                    '-volid', bdisk['name'] + '_MINI',
                    '-appid', bdisk['desc'],
                    '-publisher', bdisk['dev'],
                    '-preparer', 'prepared by ' + bdisk['dev'],
                    '-eltorito-boot', 'isolinux.bin',
                    '-eltorito-catalog', 'boot.cat',
                    '-no-emul-boot',
                    '-boot-load-size', '4',
                    '-boot-info-table',
                    '-isohybrid-mbr', '{0}/root.{1}/usr/lib/syslinux/bios/isohdpfx.bin'.format(chrootdir, arch[0]),
                    '-eltorito-alt-boot',
                    '-e', 'efiboot.img',
                    '-no-emul-boot',
                    '-isohybrid-gpt-basdat',
                    '-output', isopath,
                    bootdir]
        else:
            # UNTESTED. TODO.
            # I think i want to also get rid of: -boot-load-size 4,
            # -boot-info-table, ... possiblyyy -isohybrid-gpt-basedat...
            cmd = ['/usr/bin/xorriso',
                    '-as', 'mkisofs',
                    '-iso-level', '3',
                    '-full-iso9660-filenames',
                    '-volid', bdisk['name'] + '_MINI',
                    '-appid', bdisk['desc'],
                    '-publisher', bdisk['dev'],
                    '-preparer', 'prepared by ' + bdisk['dev'],
                    '-eltorito-boot', 'isolinux/isolinux.bin',
                    '-eltorito-catalog', 'isolinux/boot.cat',
                    '-no-emul-boot',
                    '-boot-load-size', '4',
                    '-boot-info-table',
                    '-isohybrid-mbr', '{0}/root.{1}/usr/lib/syslinux/bios/isohdpfx.bin'.format(chrootdir, arch[0]),
                    '-no-emul-boot',
                    '-isohybrid-gpt-basdat',
                    '-output', isopath,
                    bootdir]
        DEVNULL = open(os.devnull, 'w')
        subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        # Get size of ISO
        iso['name'] = ['Mini']
        iso['Mini'] = {}
        iso['Mini']['sha'] = hashlib.sha256()
        with open(isopath, 'rb') as f:
            while True:
                stream = f.read(65536)  # 64kb chunks
                if not stream:
                    break
                iso['Mini']['sha'].update(stream)
        iso['Mini']['sha'] = iso['Mini']['sha'].hexdigest()
        iso['Mini']['file'] = isopath
        iso['Mini']['size'] = humanize.naturalsize(os.path.getsize(isopath))
        iso['Mini']['type'] = 'Mini'
        iso['Mini']['fmt'] = 'Hybrid ISO'
        return(iso)

def tftpbootEnv(conf):
    build = conf['build']
    ipxe = conf['ipxe']
    sync = conf['sync']
    if sync['tftp']:
        pass  # TODO: generate a pxelinux.cfg in bdisk/tftp.py (to write) and sync in the ipxe chainloader here
