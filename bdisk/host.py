import os
import sys
import platform
import re
import configparser
from socket import getaddrinfo

def getOS():
    # Returns one of: SuSE, debian, fedora, redhat, centos, mandrake,
    # mandriva, rocks, slackware, yellowdog, gentoo, UnitedLinux,
    # turbolinux, arch, mageia
    distro = list(platform.linux_distribution())[0].lower()
    return(distro)

def getBits():
    bits = list(platform.architecture())[0]
    return(bits)

def getConfig(conf_file='/etc/bdisk/build.ini'):
    conf = False
    # define some defailt conf paths in case we're installed by
    # a package manager. in order of the paths we should search.
    default_conf_paths = ['/etc/bdisk/build.ini',
                        '/usr/share/bdisk/build.ini',
                        '/usr/share/bdisk/extra/build.ini',
                        '/usr/share/docs/bdisk/build.ini',
                        '/opt/dev/bdisk/build.ini',
                        '/opt/dev/bdisk/extra/build.ini']
        # if we weren't given one/using the default...
    if conf_file == '/etc/bdisk/build.ini':
        if not os.path.isfile(conf_file):
            for p in default_conf_paths:
                if os.path.isfile(p):
                    conf = p
                    break
    else:
        conf = conf_file
    if not conf:
        # okay, so let's check for distributed/"blank" ini's then since we can't seem to find one.
        dist_conf_paths = [re.sub('(build\.ini)','dist.\\1', s) for s in default_conf_paths]
        for q in dist_conf_paths:
            if os.path.isfile(q):
                conf = q
                break
    return(conf)

def parseConfig(conf):
    # The following are paths; c means create, e means must exist, ? means depends on other opts:
    # build:basedir(e),build:archboot(c),build:isodir(c),build:mountpt(c),
    #   build:srcdir(c),build:tempdir(c),http:path(c?),tftp:path(c?),rsync:path (remote, no op)
    # The following are files: ipxe:ssl_ca(e?),ipxe:ssl_cakey(e?),ipxe:ssl_crt(e?),ipxe:key(c)
    # The following are URIs: ipxe:uri
    # The rest are strings.
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(conf)
    config_dict = {s:dict(config.items(s)) for s in config.sections()}
    # Convert the booleans to pythonic booleans in the dict...
    config_dict['bdisk']['user'] = config['bdisk'].getboolean('user')
    conifg_dict['build']['i_am_a_racecar'] = config['build'].getboolean('i_am_a_racecar')
    conifg_dict['build']['multiarch'] = config['build'].getboolean('multiarch')
    for i in ('http', 'tftp', 'rsync', 'git'):
        config_dict['sync'][i] = config['sync'].getboolean(i)
    config_dict['ipxe']['iso'] = config['ipxe'].getboolean('iso')
    config_dict['ipxe']['usb'] = config['ipxe'].getboolean('usb')
    # Validate the rsync host. Works for IP address too. It does NOT
    # check to see if we can actually *rsync* to it; that'll come later.
    try:
        getaddrinfo(config_dict['rsync']['host'], None)
    except:
        exit(('ERROR: {0} is not a valid host that can be used for rsyncing.' +
                'Check your configuration.').format(config_dict['rsync']['host']))
    # Validate the URI.

    return(config, config_dict)
