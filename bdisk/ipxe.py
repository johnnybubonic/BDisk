import os
import shutil
import jinja2
import gitpython


def buildIPXE(conf):
    build = conf['build']
    bdisk = conf['bdisk']
    ipxe = conf['ipxe']
    templates_dir = build['basedir'] + '/extra/templates'
    patches_dir = build['basedir'] + 
    pass
