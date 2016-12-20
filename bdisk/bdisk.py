#!/bin/env python3
import host
import prep
import bchroot
import build
import datetime
import bSSL
import ipxe
import bsync
import bGPG

# we need to:
# we also need to figure out how to implement "mentos" (old bdisk) like functionality, letting us reuse an existing chroot install if possible to save time for future builds.
#   if not, though, it's no big deal.
# still on the todo: iPXE
if __name__ == '__main__':
    print('{0}: Starting.'.format(datetime.datetime.now()))
    conf = host.parseConfig(host.getConfig())[1]
    prep.dirChk(conf)
    conf['gpgobj'] = bGPG.genGPG(conf)
    prep.buildChroot(conf, keep = False)
    prep.prepChroot(conf)
    arch = conf['build']['arch']
    bGPG.killStaleAgent(conf)
    for a in arch:
        bchroot.chroot(conf['build']['chrootdir'] + '/root.' + a, 'bdisk.square-r00t.net')
        bchroot.chrootUnmount(conf['build']['chrootdir'] + '/root.' + a)
    prep.postChroot(conf['build'])
    bchroot.chrootTrim(conf['build'])
    build.genImg(conf)
    build.genUEFI(conf['build'], conf['bdisk'])
    fulliso = build.genISO(conf)
    bGPG.signIMG(fulliso['Main']['file'], conf)
    build.displayStats(fulliso)
    if conf['build']['ipxe']:
        bSSL.sslPKI(conf)
        ipxe.buildIPXE(conf)
        iso = ipxe.genISO(conf)
        if iso:
            for x in iso.keys():
                if x != 'name':
                    path = iso[x]['file']
                    bGPG.signIMG(path, conf)
            build.displayStats(iso)
    bsync.http(conf)
    bsync.tftp(conf)
    bsync.git(conf)
    bsync.rsync(conf)
    print('{0}: Finish.'.format(datetime.datetime.now()))
