import host
import prep
import bchroot

# we need to:
# 1.) import the config- this gives us info about things like build paths, etc. host.parseConfig(host.getConfig()) should do this
# 2.) prep.dirChk
# 3.) prep.downloadTarball
# 4.) prep.unpackTarball
# 5.) prep.buildChroot
# 6.) prep.prepChroot
# 7.) bchroot.chrootCmd (TODO)- this should run the <chroot>/root/pre-build.sh script
# 7.5) ....figure out a way to get those dirs to *un*mount... and only mount in 7. if they're not currently mounted.
# 8.) build.chrootClean (TODO) see jenny_craig in old bdisk. i can *probably* do this within the chroot for the most part as part of pre-build.sh
# 9.) build.genImg (TODO)- build the squashed image, etc. see will_it_blend in old bdisk
# 10.) build.genUEFI (TODO)- build the uefi binary/bootloading. see stuffy in old bdisk
# 11.) build.genISO (TODO)- build the .iso file (full boot). see yo_dj in old bdisk
#
# we also need to figure out how to implement "mentos" (old bdisk) like functionality, letting us reuse an existing chroot install if possible to save time for future builds.
#   if not, though, it's no big deal.
if __name__ == '__main__':
    # TODO: config for chrootdir, dlpath
    conf = host.parseConfig(host.getConfig())[1]
    prep.dirChk(conf)
    if conf['build']['multiarch']:
        for arch in ('x86_64', 'i686'):
            #prep.unpackTarball(prep.downloadTarball(arch, '/var/tmp/bdisk'), '/var/tmp/chroot/' + arch)
            prep.buildChroot(arch, '/var/tmp/chroot/' + arch, '/var/tmp/bdisk', conf['build']['basedir'] + '/extra')
            prep.prepChroot(conf['build']['basedir'] + '/extra/templates', '/var/tmp/chroot/' + arch, conf['bdisk'], arch)
            bchroot.chroot('/var/tmp/chroot/' + arch, 'bdisk.square-r00t.net')
            bchroot.chrootUnmount('/var/tmp/chroot/' + arch)
    else:
        # TODO: implement specific-arch building or separate building instances
        for arch in ('x86_64', 'i686'):
            #prep.unpackTarball(prep.downloadTarball(arch, '/var/tmp/bdisk'), '/var/tmp/chroot/' + arch)
            prep.buildChroot(arch, '/var/tmp/chroot/' + arch, '/var/tmp/bdisk', conf['build']['basedir'] + '/extra')
            prep.prepChroot(conf['build']['basedir'] + '/extra/templates', '/var/tmp/chroot/' + arch, conf['bdisk'], arch)
            bchroot.chroot('/var/tmp/chroot/' + arch, 'bdisk.square-r00t.net')
            bchroot.chrootUnmount('/var/tmp/chroot/' + arch)
