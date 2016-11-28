import os
import tarfile
import shutil
import glob
import subprocess
import hashlib
import jinja2
from urllib.request import urlopen


def genImg(build):
    arch = build['arch']
    chrootdir = build['chrootdir']
    archboot = build['archboot']
    hashes = {}
    hashes['sha256'] = {}
    hashes['md5'] = {}
    for a in arch:
        # Create the squashfs image
        airoot = archboot + '/' + a + '/'
        squashimg = airoot + 'airootfs.sfs'
        os.makedirs(airoot, exist_ok = True)
        print("Generating squashed filesystem image for {0}. Please wait...".format(chrootdir))
        cmd = ['/usr/bin/squashfs-tools', chrootdir, squashimg, '-noappend', '-comp', 'xz']
        proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, bufsize = 1)
        #for line in iter(proc.stdout.readline, b''):
        for line in iter(proc.stdout.readline, ''):
            print(line)
        p.stdout.close()
        p.wait()
        # Generate the checksum files
        print("Now generating SHA256 and MD5 hash checksum files for {0}. Please wait...".format(squashimg))
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


def genUEFI(build, bdisk):
    arch = build['arch']
    # 32-bit EFI implementations are nigh nonexistant.
    # We don't really need to worry about them.
    # Plus there's always multiarch.
    # I can probably do this better with a dict... TODO.
    if 'x86_64' in arch:
        os.makedirs(tempdir + '/EFI/boot', exist_ok = True)
        tempdir = build['tempdir']
        basedir = build['basedir']
        templates_dir = build['basedir'] + '/extra/templates'
        efiboot_img = tempdir + '/EFI/' + bdisk['name'] + '/efiboot.img'
        ## Download the EFI shells if we don't have them.
        # For UEFI 2.3+ (http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=UEFI_Shell)
        if not os.path.isfile(tempdir + '/EFI/shellx64_v2.efi'):
            shell2_path = tempdir + '/EFI/shellx64_v2.efi'
            print("You are missing {0}. We'll download it for you.".format(shell2_path))
            shell2_url = 'https://github.com/tianocore/edk2/blob/master/ShellBinPkg/UefiShell/X64/Shell.efi?raw=true'
            shell2_fetch = urlopen(shell2_url)
            with open(shell2_path, 'wb+') as dl:
                dl.write(shell2_fetch.read())
            shell2_fetch.close()
        # Shell for older versions (http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=Efi-shell)
        # TODO: is there an Arch package for this? can we just install that in the chroot and copy the shell binaries?
        if not os.path.isfile(tempdir + '/EFI/shellx64_v1.efi'):
            shell1_path = tempdir + '/EFI/shellx64_v1.efi'
            print("You are missing {0}. We'll download it for you.".format(shell1_path))
            shell1_url = 'https://github.com/tianocore/edk2/blob/master/EdkShellBinPkg/FullShell/X64/Shell_Full.efi?raw=true'
            shell1_fetch = urlopen(shell1_url)
            with open(shell1_path, 'wb+') as dl:
                dl.write(shell1_fetch.read())
            shell1_fetch.close()
        print("Now configuring UEFI bootloading...")
        ## But wait! That's not all! We need more binaries.
        # http://blog.hansenpartnership.com/linux-foundation-secure-boot-system-released/
        shim_url = 'http://blog.hansenpartnership.com/wp-uploads/2013/'
        for f in ('bootx64.efi', 'HashTool.efi'):
            if not os.path.isfile(tempdir + '/EFI/boot/' + f):
                url = shim_url + f
                url_fetch = urlopen(url)
                with open(tempdir + '/EFI/boot/' + f) as dl:
                    dl.write(url_fetch.read())
                url_fetch.close()
        # And we also need the systemd efi bootloader.
        if os.path.isfile(tempdir + '/EFI/boot/loader.efi'):
            os.remove(tempdir + '/EFI/boot/loader.efi')
        shutil.copy2(chrootdir + '/root.x86_64/usr/lib/systemd/boot/efi/systemd-bootx64.efi', tempdir + '/EFI/boot/loader.efi')
        # And the accompanying configs for the systemd efi bootloader, too.
        loader = jinja2.FileSystemLoader(templates_dir)
        env = jinja2.Environment(loader = loader)
        os.makedirs(tempdir + '/loader/entries', exist_ok = True)
        for t in ('loader', 'ram', 'base', 'uefi2', 'uefi1'):
            if t == 'base':
                fname = bdisk['uxname'] + '.conf'
            elif ('uefi1', 'uefi2') in t:
                fname = t + '.conf'
            else:
                fname = bdisk['uxname'] + '_' + t + '.conf'
            if t == 'loader':
                tplpath = tempdir + '/loader/'
                fname = 'loader.conf'  # we change the var from above because it's an oddball.
            else:
                tplpath = tempdir + '/loader/entries/'
            tpl = env.get_template(t)
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            with open(tplpath + fname, "w+") as f:
                f.write(tpl_out)
        # And we need to get filesizes (in bytes) for everything we need to include in the ESP.
        # This is more important than it looks.
        sizetotal = 786432  # we start with 768KB and add to it for wiggle room
        sizefiles = ['/boot/' + bdisk['uxname'] + '.64.img',
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
        # And now we create the file...
        print("Now creating a {0} bytes EFI ESP image at {1}. Please wait...".format(sizetotal, efiboot_img))
        if os.path.isfile(efiboot_img):
            os.remove(efiboot_img)
        with open(efiboot_img, 'w+') as f:
            f.truncate(sizetotal)
        cmd = ['/sbin/mkfs.vfat', '-F', '32', '-n', bdisk['name'] + '_EFI', efiboot_img]
        subprocess.call(cmd)
        cmd = ['/bin/mount', efiboot_img, build['mountpt']]
        subprocess.call(cmd)
        os.makedirs(build['mountpt'] + '/' + bdisk['name'])
        os.makedirs(build['mountpt'] + '/EFI/boot')
        os.makedirs(build['mountpt'] + '/loader/entries')
        # Ready for some deja vu? This is because it uses an embedded version as well for hybrid ISO.
        # I think.
        # TODO: just move this to a function instead, with "efi" as a param and change
        # the templates to use "if efi == 'yes'" instead.
        # function should set the "installation" path for the conf as well based on the value of efi
        # parameter.
        loader = jinja2.FileSystemLoader(templates_dir)
        env = jinja2.Environment(loader = loader)
        os.makedirs(build['mountpt'] + 'loader/entries', exist_ok = True)
        for t in ('loader', 'ram', 'base', 'uefi2', 'uefi1'):
            if t == 'base':
                fname = bdisk['uxname'] + '.conf'
            elif ('uefi1', 'uefi2') in t:
                fname = t + '.conf'
            else:
                fname = bdisk['uxname'] + '_' + t + '.conf'
            if t == 'loader':
                tplpath = build['mountpt'] + '/loader/'
                fname = 'loader.conf'  # we change the var from above because it's an oddball.
            else:
                tplpath = build['mountpt'] + '/loader/entries/'
            tpl = env.get_template(t)
            tpl_out = tpl.render(build = build, bdisk = bdisk, efi = 'yes')
            with open(tplpath + fname, "w+") as f:
                f.write(tpl_out)
            for x in ('bootx64.efi', 'HashTool.efi', 'loader.efi', 'shellx64_v1.efi', 'shellx64_v2.efi'):
                y = tempdir + '/EFI/boot/' + x
                z = mountpt + '/EFI/boot/' + x
                if os.path.isfile(z):
                    os.remove(z)
                shutil.copy(y, z)
        cmd = ['/bin/umount', mountpt]
        subprocess.call(cmd)
        return(efiboot_img)

def genISO(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    archboot = build['archboot']
    tempdir = build['tempdir']
    builddir = tempdir + '/' + bdisk['name']
    extradir = build['basedir'] + '/extra/'
    # arch[0] is safe to use, even if multiarch, because the only cases when it'd be ambiguous
    # is when x86_64 is specifically set to [0]. See host.py's parseConfig().
    syslinuxdir = build['chrootdir'] + '/root.' + arch[0] + '/usr/lib/syslinux/'
    sysl_tmp = tempdir + '/isolinux/'
    ver = build['ver']
    isofile = '{0}-{1}.iso'.format(bdisk['uxname'], bdisk['ver'])
    isopath = build['isodir'] + '/' + isofile
    arch = build['arch']
    # In case we're building a single-arch ISO...
    if len(arch) == 1:
        isolinux_cfg = extradir + 'templates/BIOS/isolinux.cfg.arch.j2'
        if arch[0] == 'i686':
            bitness = '32'
        elif arch[0] == 'x86_64':
            bitness = '64'
    if build['ipxe']:
        ipxe = conf['ipxe']
        if ipxe['iso']:
            minifile = '{0}-{1}-mini.iso'.format(bdisk['uxname'], bdisk['ver'])
            minipath = build['isodir'] + '/' + minifile
        if ipxe['usb']:
            usbfile = '{0}-{1}-mini.usb.img'.format(bdisk['uxname'], bdisk['ver'])
            minipath = build['isodir'] + '/' + usbfile
    else:
        isolinux_cfg = extradir + 'templates/BIOS/isolinux.cfg.multi.j2'
        bitness = False
    if os.path.isfile(isopath):
        os.remove(isopath)
    if archboot != tempdir + '/' + bdisk['name']:  # best to use static concat here... 
        if os.path.isdir(builddir):
            shutil.rmtree(builddir, ignore_errors = True)
        shutil.copytree(archboot, builddir)
    # Copy isolinux files
    print("Now staging some files for ISO preparation. Please wait...")
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
    # And we need to build the ISO!
    print("Now generating the full ISO at {0}. Please wait.".format(isopath))
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
    proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, bufsize = 1)
    #for line in iter(proc.stdout.readline, b''):
    for line in iter(proc.stdout.readline, ''):
        print(line)
    p.stdout.close()
    p.wait()

def cleanUp():
    # TODO: clear out all of tempdir?
    pass
