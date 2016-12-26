import os
import sys
import platform
import re
import glob
import configparser
import validators
import git
import datetime
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

def getHostname():
    hostname = platform.node()
    return(hostname)

def getConfig(conf_file='/etc/bdisk/build.ini'):
    conf = False
    # define some defailt conf paths in case we're installed by
    # a package manager. in order of the paths we should search.
    default_conf_paths = ['/etc/bdisk/build.ini',
                        '/usr/share/bdisk/build.ini',
                        '/usr/share/bdisk/extra/build.ini',
                        '/usr/share/docs/bdisk/build.ini',  # this is the preferred installation path for packagers
                        '/usr/local/etc/bdisk/build.ini',
                        '/usr/local/share/docs/bdisk/build.ini',
                        '/opt/dev/bdisk/build.ini',
                        '/opt/dev/bdisk/extra/build.ini',
                        '/opt/dev/bdisk/extra/dist.build.ini']
        # if we weren't given one/using the default...
    if conf_file == '/etc/bdisk/build.ini':
        if not os.path.isfile(conf_file):
            for p in default_conf_paths:
                if os.path.isfile(p):
                    conf = p
                    break
    else:
        conf = conf_file
    defconf = '{0}/../extra/dist.build.ini'.format(os.path.dirname(os.path.realpath(__file__)))
    if not conf:
        # okay, so let's check for distributed/"blank" ini's
        # since we can't seem to find one.
        dist_conf_paths = [re.sub('(build\.ini)','dist.\\1', s) for s in default_conf_paths]
        for q in dist_conf_paths:
            if os.path.isfile(q):
                conf = q
                break
        if os.path.isfile(default_conf_paths[4]):
            defconf = default_conf_paths[4]
    confs = [defconf, conf]
    return(confs)

def parseConfig(confs):
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(confs)
    # a dict makes this so much easier.
    config_dict = {s:dict(config.items(s)) for s in config.sections()}
    # Convert the booleans to pythonic booleans in the dict...
    config_dict['bdisk']['user'] = config['bdisk'].getboolean('user')
    config_dict['build']['gpg'] = config['build'].getboolean('gpg')
    config_dict['build']['i_am_a_racecar'] = config['build'].getboolean('i_am_a_racecar')
    config_dict['build']['ipxe'] = config['build'].getboolean('ipxe')
    config_dict['build']['multiarch'] = (config_dict['build']['multiarch']).lower()
    config_dict['ipxe']['iso'] = config['ipxe'].getboolean('iso')
    config_dict['ipxe']['usb'] = config['ipxe'].getboolean('usb')
    config_dict['sync']['git'] = config['sync'].getboolean('git')
    config_dict['sync']['http'] = config['sync'].getboolean('http')
    config_dict['sync']['rsync'] = config['sync'].getboolean('rsync')
    config_dict['sync']['tftp'] = config['sync'].getboolean('tftp')
    config_dict['rsync']['iso'] = config['rsync'].getboolean('iso')
    # Get the version...
    # Two possibilities.
    # e.g. 1 commit after tag with 7-digit object hex: ['v3.10', '1', 'gb4a5e40']
    # Or if were sitting on a tag with no commits: ['v3.10']
    # So we want our REAL version to be the following:
    # Tagged release:  v#.##
    # X number of commits after release: v#.##rX
    # Both have the (local) build number appended to the deliverables,
    # which is reset for an empty isodir OR a new tagged release (incl.
    # commits on top of a new tagged release). e.g. for build Y:
    # v#.##-Y or v#.##rX-Y
    if config_dict['bdisk']['ver'] == '':
        repo = git.Repo(config_dict['build']['basedir'])
        refs = repo.git.describe(repo.head.commit).split('-')
        if len(refs) >= 2:
            config_dict['bdisk']['ver'] = refs[0] + 'r' + refs[1]
        else:
            config_dict['bdisk']['ver'] = refs[0]
    # And the build number.
    # TODO: support tracking builds per version. i.e. in buildnum:
    # v2.51r13:0
    # v2.51r17:3
    if os.path.isfile(config_dict['build']['dlpath'] + '/buildnum'):
        with open(config_dict['build']['dlpath'] + '/buildnum', 'r') as f:
            config_dict['build']['buildnum'] = int(f.readlines()[0])
    else:
        config_dict['build']['buildnum'] = 0
    # But logically we should start the build over at 0 if we don't have any existing ISO's.
    if os.path.isdir(config_dict['build']['isodir']):
        if os.listdir(config_dict['build']['isodir']) == []:
            config_dict['build']['buildnum'] = 0
        # ...or if we don't have any previous builds for this ISO version.
        elif not glob.glob('{0}/*v{1}r*.iso'.format(config_dict['build']['isodir'], config_dict['bdisk']['ver'])):
            config_dict['build']['buildnum'] = 0
    # and build a list of arch(es) we want to build
    if config_dict['build']['multiarch'] in ('','yes','true','1','no','false','0'):
        config_dict['build']['arch'] = ['x86_64','i686']
    elif config_dict['build']['multiarch'] in ('x86_64','64','no32'):
        config_dict['build']['arch'] = ['x86_64']
    elif config_dict['build']['multiarch'] in ('i686','32','no64'):
        config_dict['build']['arch'] = ['i686']
    else:
        exit(('{0}: ERROR: {1} is not a valid value. Check your configuration.').format(
                                        datetime.datetime.now(),
                                        config_dict['build']['multiarch']))
    ## VALIDATORS ##
    # Validate bootstrap mirror
    if (validators.domain(config_dict['build']['mirror']) or validators.ipv4(
                                config_dict['build']['mirror']) or validatords.ipv6(
                                config_dict['build']['mirror'])):
        try:
            getaddrinfo(config_dict['build']['mirror'], None)
        except:
            exit(('{0}: ERROR: {1} does not resolve and cannot be used as a ' + 
                'mirror for the bootstrap tarballs. Check your configuration.').format(
                                        datetime.datetime.now(),
                                        config_dict['build']['host']))
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
                exit(('{0}: ERROR: {1} does not resolve and cannot be used for rsyncing.' +
                    'Check your configuration.').format(
                                            datetime.datetime.now(),
                                            config_dict['rsync']['host']))
        else:
            exit(('{0}: ERROR: {1} is not a valid host and cannot be used for rsyncing.' +
                    'Check your configuration.').format(
                                            datetime.datetime.now(),
                                            config_dict['rsync']['host']))
    # Validate the URI.
    if config_dict['build']['ipxe']:
        # so this won't validate e.g. custom LAN domains (https://pxeserver/bdisk.php). TODO.
        if not validators.url(config_dict['ipxe']['uri']):
            if not re.match('^https?://localhost(/.*)?$'):
                exit('{0}: ERROR: {1} is not a valid URL/URI. Check your configuration.'.format(
                                            datetime.datetime.now(),
                                            config_dict['ipxe']['uri']))
    # Validate required paths
    if not os.path.exists(config_dict['build']['basedir'] + '/extra'):
        exit(("{0}: ERROR: {1} does not contain BDisk's core files!" + 
                "Check your configuration.").format(
                                            datetime.datetime.now(),
                                            config_dict['build']['basedir']))
    # Make dirs if they don't exist
    for d in ('archboot', 'isodir', 'mountpt', 'srcdir', 'prepdir'):
        os.makedirs(config_dict['build'][d], exist_ok = True)
    # Make dirs for sync staging if we need to
    for x in ('http', 'tftp'):
        if config_dict['sync'][x]:
            os.makedirs(config_dict[x]['path'], exist_ok = True)
    return(config, config_dict)
