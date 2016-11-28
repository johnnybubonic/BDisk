import os
import shutil
import jinja2
import gitpython


def buildIPXE(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    templates_dir = build['basedir'] + '/extra/templates'
    ipxe_tpl = templates_dir + '/iPXE'
    patches_dir = ipxe_tpl + '/patches'
    srcdir = build['srcdir']
    ipxe_src = srcdir + '/ipxe'
    ipxe_git_uri = 
    pass
