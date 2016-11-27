#!/bin/env python3
import host
import prep
import bchroot
import build

# we need to:
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
    prep.buildChroot(conf['build'])
    prep.prepChroot(conf['build']['basedir'] + '/extra/templates', conf['build'], conf['bdisk'])
    arch = conf['build']['arch']
    for a in arch:
        bchroot.chroot(conf['build']['chrootdir'] + '/root.' + a, 'bdisk.square-r00t.net')
        bchroot.chrootUnmount(conf['build']['chrootdir'] + '/root.' + a)
    build.chrootClean(conf['build'])
