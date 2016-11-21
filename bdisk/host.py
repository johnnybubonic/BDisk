import os
import sys
import platform
import re
import configparser
import validators
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
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(conf)
    # a dict makes this so much easier.
    config_dict = {s:dict(config.items(s)) for s in config.sections()}
    # Convert the booleans to pythonic booleans in the dict...
    config_dict['bdisk']['user'] = config['bdisk'].getboolean('user')
    conifg_dict['build']['i_am_a_racecar'] = config['build'].getboolean('i_am_a_racecar')
    conifg_dict['build']['multiarch'] = config['build'].getboolean('multiarch')
    for i in ('http', 'tftp', 'rsync', 'git'):
        config_dict['sync'][i] = config['sync'].getboolean(i)
    config_dict['ipxe']['iso'] = config['ipxe'].getboolean('iso')
    config_dict['ipxe']['usb'] = config['ipxe'].getboolean('usb')
    ## VALIDATORS ##
    # Are we rsyncing? If so, validate the rsync host.
    # Works for IP address too. It does NOT check to see if we can
    # actually *rsync* to it; that'll come later.
    if config_dict['sync']['rsync']:
        if (validators.domain(config_dict['rsync']['host']) or validators.ipv4(
                                config_dict['rsync']['host']) or validators.ipv6(
                                config_dict['rsync']['host'])):
            try:
                getaddrinfo(config_dict['rsync']['host'], None)
            except:
                exit(('ERROR: {0} does not resolve and cannot be used for rsyncing.' +
                    'Check your configuration.').format(config_dict['rsync']['host']))
        else:
            exit(('ERROR: {0} is not a valid host and cannot be used for rsyncing.' +
                    'Check your configuration.').format(config_dict['rsync']['host']))
    # Validate the URI.
    if config_dict['sync']['ipxe']:
        # so this won't validate e.g. custom LAN domains (https://pxeserver/bdisk.php). TODO.
        if not validators.url(config_dict['ipxe']['uri']):
            if not re.match('^https?://localhost(/.*)?$'):
                exit('ERROR: {0} is not a valid URL/URI. Check your configuration.'.format(
                        config_dict['ipxe']['uri']))
    # Validate required paths
    if not os.path.exists(config_dict['build']['basedir'] + '/extra'):
        exit(("ERROR: {0} does not contain BDisk's core files!" + 
                "Check your configuration.").format(config_dict['build']['basedir']))
    # Make dirs if they don't exist
    for d in ('archboot', 'isodir', 'mountpt', 'srcdir', 'tempdir'):
        os.makedirs(config_dict['build'][d], exists_ok = True)
    # Make dirs for sync staging if we need to
    for x in ('http', 'tftp'):
        if config_dict['sync'][x]:
            os.makedirs(config_dict[x]['path'], exist_ok = True)
    # Hoo boy. Now we test paths for SSL in iPXE...
    if config_dict['build']['ipxe']:
        if config_dict['ipxe']['ssl_crt']:
            for x in ('ssl_key', 'ssl_cakey'):
                if config_dict['ipxe'][x]:
                    if not os.path.isfile(config_dict['ipxe'][x]):
                        exit(('ERROR: {0} is not an existing file. Check your' +
                                'configuration.').format(config_dict['ipxe'][x]))
            if config_dict['ipxe']['ssl_ca']:
                    if not os.path.isfile(config_dict['ipxe']['ssl_ca']):
                        exit(('ERROR: {0} is not an existing file. Check your' +
                                'configuration.').format(config_dict['ipxe']['ssl_ca']))


    return(config, config_dict)
