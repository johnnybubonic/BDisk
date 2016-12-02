#!/bin/env python3
import host
import prep
import bchroot
import build
import datetime

# we need to:
# 9.) build.genImg (TODO)- build the squashed image, etc. see will_it_blend in old bdisk
# 9.5) copy the files also in the same script. after the commented-out mtree-generation
#
# we also need to figure out how to implement "mentos" (old bdisk) like functionality, letting us reuse an existing chroot install if possible to save time for future builds.
#   if not, though, it's no big deal.
if __name__ == '__main__':
    print('Starting at {0}.'.format(datetime.datetime.now()))
    conf = host.parseConfig(host.getConfig())[1]
    prep.dirChk(conf)
    prep.buildChroot(conf['build'])
    prep.prepChroot(conf['build'], conf['bdisk'], conf['user'])
    arch = conf['build']['arch']
    for a in arch:
        bchroot.chroot(conf['build']['chrootdir'] + '/root.' + a, 'bdisk.square-r00t.net')
        bchroot.chrootUnmount(conf['build']['chrootdir'] + '/root.' + a)
    prep.postChroot(conf['build'])
    build.genImg(conf['build'], conf['bdisk'])
    build.genUEFI(conf['build'], conf['bdisk'])
    fulliso = build.genISO(conf)
    build.displayStats(fulliso)
    print('Finished successfully at {0}.'.format(datetime.datetime.now()))
