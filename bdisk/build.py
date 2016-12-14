import os
import tarfile
import shutil
import glob
import subprocess
import hashlib
import gnupg
import jinja2
import humanize
import datetime
from urllib.request import urlopen


def genImg(conf):
    bdisk = conf['bdisk']
    build = conf['build']
    arch = build['arch']
    chrootdir = build['chrootdir']
    archboot = build['archboot']
    basedir = build['basedir']
    tempdir = build['tempdir']
    hashes = {}
    hashes['sha256'] = {}
    hashes['md5'] = {}
    squashfses = []
    for a in arch:
        if a == 'i686':
            bitness = '32'
        elif a == 'x86_64':
            bitness = '64'
        # Create the squashfs image
        airoot = archboot + '/' + a + '/'
        squashimg = airoot + 'airootfs.sfs'
        os.makedirs(airoot, exist_ok = True)
        print("{0}: [BUILD] Squashing filesystem ({1})...".format(
                                                datetime.datetime.now(),
                                                chrootdir + '/root.' + a))
        # TODO: use stdout and -progress if debugging is enabled. the below subprocess.call() just redirects to
        # /dev/null.
        DEVNULL = open(os.devnull, 'w')
        cmd = ['/usr/bin/mksquashfs',
                chrootdir + '/root.' + a,
                squashimg,
                '-no-progress',
                '-noappend',
                '-comp', 'xz']
        subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        print("{0}: [BUILD] Generated {1} ({2}).".format(
                                            datetime.datetime.now(),
                                            squashimg,
                                            humanize.naturalsize(
                                                os.path.getsize(squashimg))))
        # Generate the checksum files
        print("{0}: [BUILD] Generating SHA256, MD5 checksums ({1})...".format(
                                                datetime.datetime.now(),
                                                squashimg))
        hashes['sha256'][a] = hashlib.sha256()
        hashes['md5'][a] = hashlib.md5()
        with open(squashimg, 'rb') as f:
            while True:
                stream = f.read(65536)  # 64kb chunks
                if not stream:
                    break
                # NOTE: these items are hashlib objects, NOT strings!
                hashes['sha256'][a].update(stream)
                hashes['md5'][a].update(stream)
        with open(airoot + 'airootfs.sha256', 'w+') as f:
            f.write("{0}  airootfs.sfs".format(hashes['sha256'][a].hexdigest()))
        with open(airoot + 'airootfs.md5', 'w+') as f:
            f.write("{0}  airootfs.sfs".format(hashes['md5'][a].hexdigest()))
        squashfses.append('{0}'.format(squashimg))
        print("{0}: [BUILD] Hash checksums complete.".format(datetime.datetime.now()))
        # Logo
        os.makedirs(tempdir + '/boot', exist_ok = True)
        if not os.path.isfile('{0}/extra/{1}.png'.format(basedir, bdisk['uxname'])):
            shutil.copy2(basedir + '/extra/bdisk.png', '{0}/{1}.png'.format(tempdir, bdisk['uxname']))
        else:
            shutil.copy2(basedir + '/extra/{0}.png'.format(bdisk['uxname']), '{0}/{1}.png'.format(tempdir, bdisk['uxname']))
        # Kernels, initrds...
        # We use a dict here so we can use the right filenames...
        # I might change how I handle this in the future.
        bootfiles = {}
        bootfiles['kernel'] = ['vmlinuz-linux-' + bdisk['name'], '{0}.{1}.kern'.format(bdisk['uxname'], bitness)]
        bootfiles['initrd'] = ['initramfs-linux-{0}.img'.format(bdisk['name']), '{0}.{1}.img'.format(bdisk['uxname'], bitness)]
        for x in ('kernel', 'initrd'):
            shutil.copy2('{0}/root.{1}/boot/{2}'.format(chrootdir, a, bootfiles[x][0]), '{0}/boot/{1}'.format(tempdir, bootfiles[x][1]))
    for i in squashfses:
        signIMG(i, conf)


def genUEFI(build, bdisk):
    arch = build['arch']
    # 32-bit EFI implementations are nigh nonexistant.
    # We don't really need to worry about them.
    # Plus there's always multiarch.
    # I can probably do this better with a dict... TODO.
    if 'x86_64' in arch:
        tempdir = build['tempdir']
        basedir = build['basedir']
        chrootdir = build['chrootdir']
        mountpt = build['mountpt']
        templates_dir = build['basedir'] + '/extra/templates'
        efidir = '{0}/EFI/{1}'.format(tempdir, bdisk['name'])
        os.makedirs(efidir, exist_ok = True)
        efiboot_img = efidir + '/efiboot.img'
        os.makedirs(tempdir + '/EFI/boot', exist_ok = True)
        ## Download the EFI shells if we don't have them.
        # For UEFI 2.3+ (http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=UEFI_Shell)
        if not os.path.isfile(tempdir + '/EFI/shellx64_v2.efi'):
            shell2_path = tempdir + '/EFI/shellx64_v2.efi'
            print("{0}: [BUILD] Warning: You are missing {1}. Fetching...".format(datetime.datetime.now(), shell2_path))
            shell2_url = 'https://raw.githubusercontent.com/tianocore/edk2/master/ShellBinPkg/UefiShell/X64/Shell.efi'
            shell2_fetch = urlopen(shell2_url)
            with open(shell2_path, 'wb+') as dl:
                dl.write(shell2_fetch.read())
            shell2_fetch.close()
        # Shell for older versions (http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=Efi-shell)
        # TODO: is there an Arch package for this? can we just install that in the chroot and copy the shell binaries?
        if not os.path.isfile(tempdir + '/EFI/shellx64_v1.efi'):
            shell1_path = tempdir + '/EFI/shellx64_v1.efi'
            print("{0}: [BUILD] Warning: You are missing {1}. Fetching...".format(datetime.datetime.now(), shell1_path))
            shell1_url = 'https://raw.githubusercontent.com/tianocore/edk2/master/EdkShellBinPkg/FullShell/X64/Shell_Full.efi'
            shell1_fetch = urlopen(shell1_url)
            with open(shell1_path, 'wb+') as dl:
                dl.write(shell1_fetch.read())
            shell1_fetch.close()
        print("{0}: [BUILD] Building UEFI support...".format(datetime.datetime.now()))
        ## But wait! That's not all! We need more binaries.
        # http://blog.hansenpartnership.com/linux-foundation-secure-boot-system-released/
        shim_url = 'http://blog.hansenpartnership.com/wp-uploads/2013/'
        for f in ('PreLoader.efi', 'HashTool.efi'):
            if f == 'PreLoader.efi':
                fname = 'bootx64.efi'
            else:
                fname = f
            if not os.path.isfile(tempdir + '/EFI/boot/' + fname):
                url = shim_url + f
                url_fetch = urlopen(url)
                with open(tempdir + '/EFI/boot/' + fname, 'wb+') as dl:
                    dl.write(url_fetch.read())
                url_fetch.close()
        # And we also need the systemd efi bootloader.
        if os.path.isfile(tempdir + '/EFI/boot/loader.efi'):
            os.remove(tempdir + '/EFI/boot/loader.efi')
        shutil.copy2(chrootdir + '/root.x86_64/usr/lib/systemd/boot/efi/systemd-bootx64.efi', tempdir + '/EFI/boot/loader.efi')
        # And the accompanying configs for the systemd efi bootloader, too.
        tpl_loader = jinja2.FileSystemLoader(templates_dir)
        env = jinja2.Environment(loader = tpl_loader)
        os.makedirs(tempdir + '/loader/entries', exist_ok = True)
        for t in ('loader', 'ram', 'base', 'uefi2', 'uefi1'):
            if t == 'base':
                fname = bdisk['uxname'] + '.conf'
            elif t not in ('uefi1', 'uefi2'):
                fname = t + '.conf'
            else:
                fname = bdisk['uxname'] + '_' + t + '.conf'
            if t == 'loader':
                tplpath = tempdir + '/loader/'
                fname = 'loader.conf'  # we change the var from above because it's an oddball.
            else:
                tplpath = tempdir + '/loader/entries/'
            tpl = env.get_template('EFI/' + t + '.conf.j2')
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            with open(tplpath + fname, "w+") as f:
                f.write(tpl_out)
        # And we need to get filesizes (in bytes) for everything we need to include in the ESP.
        # This is more important than it looks.
        #sizetotal = 33553920  # The spec'd EFI binary size (32MB). It's okay to go over this though (and we do)
        # because xorriso sees it as a filesystem image and adjusts the ISO automagically.
        sizetotal = 2097152  # we start with 2MB and add to it for wiggle room
        sizefiles = ['/boot/' + bdisk['uxname'] + '.64.img',
                    '/boot/' + bdisk['uxname'] + '.64.kern',
                    '/EFI/boot/bootx64.efi',
                    '/EFI/boot/loader.efi',
                    '/EFI/boot/HashTool.efi',
                    '/EFI/shellx64_v1.efi',
                    '/EFI/shellx64_v2.efi']
        for i in sizefiles:
            sizetotal += os.path.getsize(tempdir + i)
        # Loader configs
        for (path, dirs, files) in os.walk(tempdir + '/loader/'):
            for file in files:
                fname = os.path.join(path, file)
                sizetotal += os.path.getsize(fname)
        # And now we create the EFI binary filesystem image/binary...
        print("{0}: [BUILD] Creating EFI ESP image {2} ({1})...".format(
                                        datetime.datetime.now(),
                                        humanize.naturalsize(sizetotal),
                                        efiboot_img))
        if os.path.isfile(efiboot_img):
            os.remove(efiboot_img)
        with open(efiboot_img, 'wb+') as f:
            f.truncate(sizetotal)
        DEVNULL = open(os.devnull, 'w')
        cmd = ['/sbin/mkfs.vfat', '-F', '32', '-n', bdisk['name'] + '_EFI', efiboot_img]
        subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
        cmd = ['/bin/mount', efiboot_img, build['mountpt']]
        subprocess.call(cmd)
        os.makedirs('{0}/EFI/{1}'.format(build['mountpt'], bdisk['name']))
        os.makedirs(build['mountpt'] + '/EFI/boot')
        os.makedirs(build['mountpt'] + '/loader/entries')
        # Ready for some deja vu? This is because it uses an embedded version as well for hybrid ISO.
        # I think.
        # TODO: just move this to a function instead, with "efi" as a param and change
        # the templates to use "if efi == 'yes'" instead.
        # function should set the "installation" path for the conf as well based on the value of efi
        # parameter.
        env = jinja2.Environment(loader = tpl_loader)
        for t in ('loader', 'ram', 'base', 'uefi2', 'uefi1'):
            if t == 'base':
                fname = bdisk['uxname'] + '.conf'
            elif t in ('uefi1', 'uefi2'):
                fname = t + '.conf'
            else:
                fname = bdisk['uxname'] + '_' + t + '.conf'
            if t == 'loader':
                tplpath = build['mountpt'] + '/loader/'
                fname = 'loader.conf'  # we change the var from above because it's an oddball.
            else:
                tplpath = build['mountpt'] + '/loader/entries/'
            tpl = env.get_template('EFI/' + t + '.conf.j2')
            tpl_out = tpl.render(build = build, bdisk = bdisk, efi = 'yes')
            with open(tplpath + fname, "w+") as f:
                f.write(tpl_out)
            for x in ('bootx64.efi', 'HashTool.efi', 'loader.efi'):
                y = tempdir + '/EFI/boot/' + x
                z = mountpt + '/EFI/boot/' + x
                if os.path.isfile(z):
                    os.remove(z)
                shutil.copy(y, z)
            for x in ('shellx64_v1.efi', 'shellx64_v2.efi'):
                y = tempdir + '/EFI/' + x
                z = mountpt + '/EFI/' + x
                if os.path.isfile(z):
                    os.remove(z)
                shutil.copy(y, z)
        shutil.copy2('{0}/root.{1}/boot/vmlinuz-linux-{2}'.format(chrootdir, 'x86_64', bdisk['name']),
                    '{0}/EFI/{1}/{2}.efi'.format(mountpt, bdisk['name'], bdisk['uxname']))
        shutil.copy2('{0}/root.{1}/boot/initramfs-linux-{2}.img'.format(chrootdir, 'x86_64', bdisk['name']),
                    '{0}/EFI/{1}/{2}.img'.format(mountpt, bdisk['name'], bdisk['uxname']))
        # TODO: support both arch's as EFI bootable instead? Maybe? requires more research. very rare.
        #shutil.copy2('{0}/root.{1}/boot/vmlinuz-linux-{2}'.format(chrootdir, a, bdisk['name']),
        #            '{0}/EFI/{1}/{2}.{3}.efi'.format(mountpt, bdisk['name'], bdisk['uxname'], bitness))
        #shutil.copy2('{0}/root.{1}/boot/initramfs-linux-{2}.img'.format(chrootdir, a, bdisk['uxname']),
        #            '{0}/EFI/{1}/{2}.{3}.img'.format(mountpt, bdisk['name'], bdisk['uxname'], bitness))
        cmd = ['/bin/umount', mountpt]
        subprocess.call(cmd)
        efisize = humanize.naturalsize(os.path.getsize(efiboot_img))
        print('{0}: [BUILD] Built EFI binary.'.format(datetime.datetime.now()))
        return(efiboot_img)

def genISO(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    archboot = build['archboot']
    tempdir = build['tempdir']
    templates_dir = build['basedir'] + '/extra/templates'
    arch = build['arch']
    builddir = tempdir + '/' + bdisk['name']
    extradir = build['basedir'] + '/extra/'
    # arch[0] is safe to use, even if multiarch, because the only cases when it'd be ambiguous
    # is when x86_64 is specifically set to [0]. See host.py's parseConfig().
    # TODO: can we use syslinux for EFI too instead of prebootloader?
    syslinuxdir = build['chrootdir'] + '/root.' + arch[0] + '/usr/lib/syslinux/bios/'
    sysl_tmp = tempdir + '/isolinux/'
    ver = bdisk['ver']
    if len(arch) == 1:
        isofile = '{0}-{1}-{2}-{3}.iso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'], arch[0])
    else:
        isofile = '{0}-{1}-{2}.iso'.format(bdisk['uxname'], bdisk['ver'], build['buildnum'])
    isopath = build['isodir'] + '/' + isofile
    arch = build['arch']
    # In case we're building a single-arch ISO...
    if len(arch) == 1:
        isolinux_cfg = '/BIOS/isolinux.cfg.arch.j2'
        if arch[0] == 'i686':
            bitness = '32'
            efi = False
        elif arch[0] == 'x86_64':
            bitness = '64'
            efi = True
    else:
        isolinux_cfg = '/BIOS/isolinux.cfg.multi.j2'
        bitness = False
        efi = True
    if os.path.isfile(isopath):
        os.remove(isopath)
    if archboot != tempdir + '/' + bdisk['name']:  # best to use static concat here... 
        if os.path.isdir(builddir):
            shutil.rmtree(builddir, ignore_errors = True)
        shutil.copytree(archboot, builddir)
    if build['ipxe']:
        ipxe = conf['ipxe']
        if ipxe['iso']:
            minifile = '{0}-{1}-mini.iso'.format(bdisk['uxname'], bdisk['ver'])
            minipath = build['isodir'] + '/' + minifile
        if ipxe['usb']:
            usbfile = '{0}-{1}-mini.usb.img'.format(bdisk['uxname'], bdisk['ver'])
            minipath = build['isodir'] + '/' + usbfile
    # Copy isolinux files
    print("{0}: [BUILD] Staging ISO preparation...".format(datetime.datetime.now()))
    isolinux_files = ['isolinux.bin',
                    'vesamenu.c32',
                    'linux.c32',
                    'reboot.c32']
    # TODO: implement debugging mode in bdisk
    #if debug:
    #   isolinux_files[0] = 'isolinux-debug.bin'
    os.makedirs(sysl_tmp, exist_ok = True)
    for f in isolinux_files:
        if os.path.isfile(sysl_tmp + f):
            os.remove(sysl_tmp + f)
        shutil.copy2(syslinuxdir + f, sysl_tmp + f)
    ifisolinux_files = ['ldlinux.c32',
                        'libcom32.c32',
                        'libutil.c32',
                        'ifcpu64.c32']
    for f in ifisolinux_files:
        if os.path.isfile(sysl_tmp + f):
            os.remove(sysl_tmp + f)
        shutil.copy2(syslinuxdir + f, sysl_tmp + f)
    tpl_loader = jinja2.FileSystemLoader(templates_dir)
    env = jinja2.Environment(loader = tpl_loader)
    tpl = env.get_template(isolinux_cfg)
    tpl_out = tpl.render(build = build, bdisk = bdisk)
    with open(sysl_tmp + '/isolinux.cfg', "w+") as f:
        f.write(tpl_out)
    # And we need to build the ISO!
    # TODO: only include UEFI support if we actually built it!
    print("{0}: [BUILD] Building full ISO ({1})...".format(datetime.datetime.now(), isopath))
    if efi:
        cmd = ['/usr/bin/xorriso',
            '-as', 'mkisofs',
            '-iso-level', '3',
            '-full-iso9660-filenames',
            '-volid', bdisk['name'],
            '-appid', bdisk['desc'],
            '-publisher', bdisk['dev'],
            '-preparer', 'prepared by ' + bdisk['dev'],
            '-eltorito-boot', 'isolinux/isolinux.bin',
            '-eltorito-catalog', 'isolinux/boot.cat',
            '-no-emul-boot',
            '-boot-load-size', '4',
            '-boot-info-table',
            '-isohybrid-mbr', syslinuxdir + 'isohdpfx.bin',
            '-eltorito-alt-boot',
            '-e', 'EFI/' + bdisk['name'] + '/efiboot.img',
            '-no-emul-boot',
            '-isohybrid-gpt-basdat',
            '-output', isopath,
            tempdir]
    else:
        # UNTESTED. TODO.
        # I think i want to also get rid of: -boot-load-size 4,
        # -boot-info-table, ... possiblyyy -isohybrid-gpt-basedat...
        cmd = ['/usr/bin/xorriso',
            '-as', 'mkisofs',
            '-iso-level', '3',
            '-full-iso9660-filenames',
            '-volid', bdisk['name'],
            '-appid', bdisk['desc'],
            '-publisher', bdisk['dev'],
            '-preparer', 'prepared by ' + bdisk['dev'],
            '-eltorito-boot', 'isolinux/isolinux.bin',
            '-eltorito-catalog', 'isolinux/boot.cat',
            '-no-emul-boot',
            '-boot-load-size', '4',
            '-boot-info-table',
            '-isohybrid-mbr', syslinuxdir + 'isohdpfx.bin',
            '-no-emul-boot',
            '-isohybrid-gpt-basdat',
            '-output', isopath,
            tempdir]
    DEVNULL = open(os.devnull, 'w')
    subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
    # Get size of ISO
    iso = {}
    iso['name'] = ['Main']
    iso['Main'] = {}
    iso['Main']['sha'] = hashlib.sha256()
    with open(isopath, 'rb') as f:
        while True:
            stream = f.read(65536)  # 64kb chunks
            if not stream:
                break
            iso['Main']['sha'].update(stream)
    iso['Main']['sha'] = iso['Main']['sha'].hexdigest()
    iso['Main']['file'] = isopath
    iso['Main']['size'] = humanize.naturalsize(os.path.getsize(isopath))
    iso['Main']['type'] = 'Full'
    iso['Main']['fmt'] = 'Hybrid ISO'
    return(iso)

def signIMG(file, conf):
    if conf['build']['gpg']:
        # If we enabled GPG signing, we need to figure out if we
        # are using a personal key or the automatically generated one.
        if conf['gpg']['mygpghome'] != '':
            gpghome = conf['gpg']['mygpghome']
        else:
            gpghome = conf['build']['dlpath'] + '/.gnupg'
        if conf['gpg']['mygpgkey'] != '':
            keyid = conf['gpg']['mygpgkey']
        else:
            keyid = False
        gpg = gnupg.GPG(gnupghome = gpghome, use_agent = True)
        # And if we didn't specify one manually, we'll pick the first one we find.
        # This way we can use the automatically generated one from prep.
        if not keyid:
            keyid = gpg.list_keys(True)[0]['keyid']
        print('{0}: [BUILD] Signing {1} with {2}...'.format(
                                        datetime.datetime.now(),
                                        file,
                                        keyid))
        # TODO: remove this warning when upstream python-gnupg fixes
        print('\t\t\t    If you see a "ValueError: Unknown status message: \'KEY_CONSIDERED\'" error, ' +
                'it can be safely ignored.')
        print('\t\t\t    If this is taking a VERY LONG time, try installing haveged and starting it. ' +
                'This can be done safely in parallel with the build process.')
        with open(file, 'rb') as fh:
            gpg.sign_file(fh, keyid = keyid, detach = True,
                            clearsign = False, output = '{0}.sig'.format(file))

def displayStats(iso):
    for i in iso['name']:
        print("{0}: == {1} {2} ==".format(datetime.datetime.now(), iso[i]['type'], iso[i]['fmt']))
        print('\t\t\t    = Size: {0}'.format(iso[i]['size']))
        print('\t\t\t    = SHA256: {0}'.format(iso[i]['sha']))
        print('\t\t\t    = Location: {0}'.format(iso[i]['file']))

def cleanUp():
    # TODO: clear out all of tempdir?
    pass
