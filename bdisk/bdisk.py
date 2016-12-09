#!/bin/env python3
import host
import prep
import bchroot
import build
import datetime
import bSSL
import ipxe

# we need to:
# we also need to figure out how to implement "mentos" (old bdisk) like functionality, letting us reuse an existing chroot install if possible to save time for future builds.
#   if not, though, it's no big deal.
# still on the todo: iPXE
if __name__ == '__main__':
    print('{0}: Starting.'.format(datetime.datetime.now()))
    conf = host.parseConfig(host.getConfig())[1]
    prep.dirChk(conf)
    prep.buildChroot(conf['build'], keep = False)
    prep.prepChroot(conf['build'], conf['bdisk'], conf['user'])
    arch = conf['build']['arch']
    for a in arch:
        bchroot.chroot(conf['build']['chrootdir'] + '/root.' + a, 'bdisk.square-r00t.net')
        bchroot.chrootUnmount(conf['build']['chrootdir'] + '/root.' + a)
    prep.postChroot(conf['build'])
    bchroot.chrootTrim(conf['build'])
    build.genImg(conf['build'], conf['bdisk'])
    build.genUEFI(conf['build'], conf['bdisk'])
    fulliso = build.genISO(conf)
    build.displayStats(fulliso)
    if conf['build']['ipxe']:
        bSSL.sslPKI(conf)
        iso = ipxe.buildIPXE(conf)
        build.displayStats(iso)
    print('{0}: Finish.'.format(datetime.datetime.now()))
