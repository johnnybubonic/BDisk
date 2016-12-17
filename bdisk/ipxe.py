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
    prepdir = conf['build']['prepdir']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    srcdir = build['srcdir']
    embedscript = build['dlpath'] + '/EMBED'
    ipxe_src = srcdir + '/ipxe'
    ipxe_git_uri = 'git://git.ipxe.org/ipxe.git'
    print('{0}: [IPXE] Prep/fetch sources...'.format(
                                        datetime.datetime.now()))
    # Get the source
    if os.path.isdir(ipxe_src):
        shutil.rmtree(ipxe_src)
    ipxe_repo = git.Repo.clone_from(ipxe_git_uri, ipxe_src)
    # Generate patches
    tpl_loader = jinja2.FileSystemLoader(ipxe_tpl)
    env = jinja2.Environment(loader = tpl_loader)
    tpl = env.get_template('EMBED.j2')
    tpl_out = tpl.render(ipxe = ipxe)
    with open(embedscript, 'w+') as f:
        f.write(tpl_out)
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
    modenv = os.environ.copy()
    modenv['EMBED'] = embedscript
    #modenv['TRUST'] = ipxe_ssl_ca  # TODO: test these
    #modenv['CERT'] = '{0},{1}'.format(ipxe_ssl_ca, ipxe_ssl_crt)  # TODO: test these
    #modenv['PRIVKEY'] = ipxe_ssl_ckey  # TODO: test these
    build_cmd = {}
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
    print('{0}: [IPXE] Built iPXE image(s) successfully.'.format(datetime.datetime.now()))
    os.chdir(cwd)

def genISO(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    arch = build['arch']
    dlpath = build['dlpath']
    ver = bdisk['ver']
    isodir = build['isodir']
    isofile = '{0}-{1}-{2}.mini.iso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    isopath = '{0}/{1}'.format(isodir, isofile)
    prepdir = build['prepdir']
    chrootdir = build['chrootdir']
    mini = ipxe['iso']
    iso = {}
    srcdir = build['srcdir']
    ipxe_src = srcdir + '/ipxe'
    mountpt = build['mountpt']
    templates_dir = build['basedir'] + '/extra/templates/iPXE/'
    tpl_loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = tpl_loader)
    bootdir = '{0}/ipxe_mini'.format(dlpath)
    efiboot_img = '{0}/EFI/{1}/efiboot.img'.format(bootdir, bdisk['name'])
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
        os.makedirs(os.path.dirname(efiboot_img), exist_ok = True)  # FAT32 embedded EFI dir
        os.makedirs('{0}/EFI/boot'.format(bootdir), exist_ok = True)  # EFI bootloader binary dir
        # Inner dir (miniboot.img file)
        #sizetotal = 2097152  # 2MB wiggle room. increase this if we add IA64.
        sizetotal = 34603008  # 33MB wiggle room. increase this if we add IA64.
        sizetotal += os.path.getsize(innerefi64)
        sizefiles = ['HashTool', 'PreLoader']
        for f in sizefiles:
            sizetotal += os.path.getsize('{0}/root.x86_64/usr/share/efitools/efi/{1}.efi'.format(
                                                        chrootdir,
                                                        f))
        # These won't be *quite* accurate since it's before the template substitution,
        # but it'll be close enough.
        for (path, dirs, files) in os.walk(templates_dir):
            for file in files:
                fname = os.path.join(path, file)
                sizetotal += os.path.getsize(fname)
        print("{0}: [IPXE] Creating EFI ESP image {1} ({2})...".format(
                                                                datetime.datetime.now(),
                                                                efiboot_img,
                                                                humanize.naturalsize(sizetotal)))
        if os.path.isfile(efiboot_img):
            os.remove(efiboot_img)
        with open(efiboot_img, 'wb+') as f:
            f.truncate(sizetotal)
        DEVNULL = open(os.devnull, 'w')
        cmd = ['/sbin/mkfs.fat', '-F', '32', '-n', 'iPXE_EFI', efiboot_img]
        subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        cmd = ['/bin/mount', efiboot_img, mountpt]
        subprocess.call(cmd)
        os.makedirs(mountpt + '/EFI/boot', exist_ok = True)  # "Inner" (EFI image)
        os.makedirs('{0}/EFI/{1}'.format(mountpt, bdisk['name']), exist_ok = True)  # "Inner" (EFI image)
        os.makedirs('{0}/boot'.format(bootdir), exist_ok = True)  # kernel(s)
        os.makedirs('{0}/loader/entries'.format(bootdir), exist_ok = True)  # EFI
        for d in (mountpt, bootdir):
            shutil.copy2(innerefi64,'{0}/EFI/boot/ipxe.efi'.format(d))
        for f in ('PreLoader.efi', 'HashTool.efi'):
            if f == 'PreLoader.efi':
                fname = 'bootx64.efi'
            else:
                fname = f
            if not os.path.isfile('{0}/EFI/boot/{1}'.format(mountpt, fname)):
                shutil.copy2('{0}/root.x86_64/usr/share/efitools/efi/{1}'.format(chrootdir, f),
                    '{0}/EFI/boot/{1}'.format(mountpt, fname))
                if not os.path.isfile('{0}/EFI/boot/{1}'.format(bootdir, f)):
                    shutil.copy2('{0}/root.x86_64/usr/share/efitools/efi/{1}'.format(chrootdir, f),
                        '{0}/EFI/boot/{1}'.format(bootdir, fname))
                # And the systemd efi bootloader.
                if not os.path.isfile('{0}/EFI/boot/loader.efi'.format(mountpt)):
                    shutil.copy2('{0}/root.x86_64/usr/lib/systemd/boot/efi/systemd-bootx64.efi'.format(chrootdir),
                                    '{0}/EFI/boot/loader.efi'.format(mountpt))
                    if not os.path.isfile('{0}/EFI/boot/loader.efi'.format(bootdir)):
                        shutil.copy2('{0}/root.x86_64/usr/lib/systemd/boot/efi/systemd-bootx64.efi'.format(chrootdir),
                                        '{0}/EFI/boot/loader.efi'.format(bootdir))
        # And loader entries.
        os.makedirs('{0}/loader/entries'.format(mountpt, exist_ok = True))
        for t in ('loader', 'base'):
            if t == 'base':
                name = bdisk['uxname']
                tplpath = '{0}/loader/entries'.format(mountpt)
            else:
                name = t
                tplpath = '{0}/loader'.format(mountpt)
            tpl = env.get_template('EFI/{0}.conf.j2'.format(t))
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            with open('{0}/{1}.conf'.format(tplpath, name), "w+") as f:
                f.write(tpl_out)
        cmd = ['/bin/umount', mountpt]
        subprocess.call(cmd)
        # Outer dir
        outerdir = True
        os.makedirs('{0}/isolinux'.format(bootdir), exist_ok = True)  # BIOS
        # and we create the loader entries (outer)
        for t in ('loader','base'):
            if t == 'base':
                name = bdisk['uxname']
                tplpath = '{0}/loader/entries'.format(bootdir)
            else:
                name = t
                tplpath = '{0}/loader'.format(bootdir)
            tpl = env.get_template('EFI/{0}.conf.j2'.format(t))
            tpl_out = tpl.render(build = build, bdisk = bdisk, outerdir = outerdir)
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
                    '-e', 'EFI/{0}/{1}'.format(bdisk['name'], os.path.basename(efiboot_img)),
                    '-no-emul-boot',
                    '-isohybrid-gpt-basdat',
                    '-output', isopath,
                    bootdir]
        else:
            # UNTESTED. TODO.
            # I think i want to also get rid of: -boot-load-size 4,
            # -boot-info-table, ... possiblyyy -isohybrid-gpt-basedat...
            # https://wiki.archlinux.org/index.php/Unified_Extensible_Firmware_Interface#Remove_UEFI_boot_support_from_Optical_Media
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
        #subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        subprocess.call(cmd)
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
