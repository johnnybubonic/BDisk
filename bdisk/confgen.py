#!/usr/bin/env python3.6

# Ironically enough, I think building a GUI for this would be *cleaner*.
# Go figure.

import confparse
import crypt
import getpass
import os
import utils
import uuid
import lxml.etree

detect = utils.detect()
generate = utils.generate()
prompt = utils.prompts()
transform = utils.transform()
valid = utils.valid()

# TODO: convert the restarts for prompts to continue's instead of letting them
#       continue on to the next prompt.

def pass_prompt(user):
    # This isn't in utils.prompts() because we need to use an instance of
    # utils.valid() and it feels like it belongs here, since it's only usable
    # for configuration generation.
    passwd = {'hashed': None,
              'password': None,
              'hash_algo': None,
              'salt': None}
    _special_password_values = ('BLANK', '')
    _passwd_is_special = False
    _need_input_type = True
    while _need_input_type:
        _input_type = input('\nWill you be entering a password or a salted '
                            'hash? (If using a "special" value per the '
                            'manual, use password entry):\n\n'
                            '\t\t1: password\n'
                            '\t\t2: salted hash\n\n'
                            'Choice: ').strip()
        if not valid.integer(_input_type):
            print('You must enter 1 or 2.')
        else:
            if int(_input_type) == 1:
                _input_type = 'password'
                _need_input_type = False
                passwd['hashed'] = False
            elif int(input_type) == 2:
                _input_type = 'salted hash'
                _need_input_type = False
                passwd['hashed'] = True
            else:
                print('You must enter 1 or 2.')
    _prompt = ('\nWhat do you want {0}\'s {1} to be?\n').format(user,
                                                                _input_type)
    if passwd['hashed']:
        passwd['password'] = input('{0}\n{1}: '.format(_prompt,
                                                       _input_type.title()))
        if not valid.password_hash:
            print('This is not a valid password hash. Re-running.')
            pass_prompt(user)
    else:
        passwd['password'] = getpass.getpass(_prompt + ('See the manual for '
                                'special values.\nYour input will NOT '
                                'echo back (unless it\'s a special value).\n'
                                '{0}: ').format(_input_type.title()))
        if passwd['password'] in _special_password_values:
            _passwd_is_special = True
            # 'BLANK' => '' => <(root)password></(root)password>
            if passwd['password'] == 'BLANK':
                passwd['password'] == ''
            # '' => None => <(root)password />
            elif passwd['password'] == '':
                passwd['password'] == None
        if not valid.password(passwd['password']):
            print('As a safety precaution, we are refusing to use this '
                  'password. It should entirely consist of the 95 printable '
                  'ASCII characters. Consult the manual\'s section on '
                  'passwords for more information.\nLet\'s try this again, '
                  'shall we?')
            pass_prompt(user)
        _salt = input('\nEnter the salt to use. If left blank, one will be '
                      'automatically generated. See the manual for special '
                      'values.\nSalt: ').strip()
        if _salt == '':
            pass
        elif _salt == 'auto':
            passwd['salt'] = 'auto'
        elif not valid.salt_hash():
            print('This is not a valid salt. Let\'s try this again.')
            pass_prompt(user)
        else:
            passwd['salt'] = _salt
        _algo = input(('\nWhat algorithm should we use to hash the password? '
                       'The default is sha512. You can choose from the '
                       'following:\n\n'
                       '\t\t{0}\n\nAlgorithm: ').format(
                                    '\n\t\t'.join(list(utils.crypt_map.keys()))
                       )).strip().lower()
        if _algo == '':
            _algo = 'sha512'
        if _algo not in utils.crypt_map:
            print('Algorithm not found; let\'s try this again.')
            pass_prompt(user)
        else:
            passwd['hash_algo'] = _algo
        if _salt == '':
            passwd['salt'] = generate.salt(_algo)
        if not _passwd_is_special:
            _gen_now = prompt.confirm_or_no(prompt = '\nGenerate a password '
                            'hash now? This is HIGHLY recommended; otherwise, '
                            'the plaintext password will be stored in the '
                            'configuration and that is no bueno.\n')
            if _gen_now:
                passwd['password'] = generate.hash_password(
                                        passwd['password'],
                                        salt = passwd['salt'],
                                        algo = passwd['hash_algo'])
                passwd['hashed'] = True
    return(passwd)

class ConfGenerator(object):
    def __init__(self, cfgfile = None, append_config = False):
        if append_config:
            if not cfgfile:
                raise RuntimeError('You have specified config appending but '
                                   'did not provide a configuration file')
            if cfgfile:
                self.cfgfile = os.path.abspath(os.path.expanduser(cfgfile))
            else:
                # Write to STDOUT
                self.cfgfile = None
            c = confparse.Conf(cfgfile)
            self.cfg = c.xml
            self.append = True
        else:
            self.cfg = lxml.etree.Element('bdisk')
            self.append = False
        self.profile = lxml.etree.Element('profile')
        self.cfg.append(self.profile)

    def main(self):
        print(('\n\tPlease consult the manual at {manual_site} if you have '
               'any questions.'
               '\n\tYou can hit CTRL-c at any time to quit.\n'
              ).format(manual_site = 'https://bdisk.square-r00t.net/'))
        try:
            self.get_profile_attribs()
            self.get_meta()
            self.get_accounts()
            self.get_sources()
            self.get_build()
            self.get_iso()
            self.get_ipxe()
            self.get_pki()
            self.get_gpg()
            self.get_sync()
        except KeyboardInterrupt:
            exit('\n\nCaught KeyboardInterrupt; quitting...')
        return()

    def get_profile_attribs(self):
        print('++ PROFILE ATTRIBUTES ++')
        id_attrs = {'name': None,
                    'id': None,
                    'uuid': None}
        while not any(tuple(id_attrs.values())):
            print('\nThese are used to uniquely identify the profile you are '
                  'creating. To ensure compatibility with other processes, '
                  'each profile MUST be unique (even if you\'re only storing '
                  'one profile per file). That means at least ONE of these '
                  'attributes must be populated. You can hit enter to leave '
                  'the attribute blank - you don\'t need to provide ALL '
                  'attributes (though it\'s certainly recommended).')
            id_attrs['name'] = transform.sanitize_input(
                                    (input(
                                '\nWhat name should this profile be? (It will '
                                'be transformed to a safe string if '
                                'necessary.)\nName: ')
                                    ))
            id_attrs['id'] = transform.sanitize_input(
                                    (input(
                '\nWhat ID number should this profile have? It MUST be a '
                'positive integer.\nID: ')
                                    ).strip())
            if id_attrs['id']:
                if not valid.integer(id_attrs['id']):
                    print('Invalid; skipping...')
                    id_attrs['id'] = None
            # We don't sanitize this because it'd break. UUID4 requires hyphen
            # separators. We still validate, though.
            id_attrs['uuid'] = input(
                '\nWhat UUID should this profile have? '
                'It MUST be a UUID4 (RFC4122 § 4.4). e.g.:\n'
                '\t333d7287-3caa-45fe-b954-2da15dad1212\n'
                'If you use the special value "auto" (without quotes), then '
                'one will be automatically generated for you.\nUUID: ').strip()
            if id_attrs['uuid'].lower() == 'auto':
                id_attrs['uuid'] = str(uuid.uuid4())
                print('\n\tGenerated a UUID: {0}\n'.format(id_attrs['uuid']))
            else:
                if not valid.uuid(id_attrs['uuid']):
                    print('Invalid; skipping...')
                    id_attrs['uuid'] = None
            # This causes a looping if none of the answers are valid.
            for i in id_attrs:
                if id_attrs[i] == '':
                    id_attrs[i] = None
        for i in id_attrs:
            if id_attrs[i]:
                self.profile.attrib[i] = id_attrs[i]
        print()
        return()

    def get_meta(self):
        print('\n++ META ITEMS ++')
        meta_items = {'names': {'name': None,
                                'uxname': None,
                                'pname': None},
                      'desc': None,
                      'uri': None,
                      'ver': None,
                      'dev': {'author': None,
                              'email': None,
                              'website': None},
                      'max_recurse': None}
        while (not transform.flatten_recurse(meta_items) or \
                            (None in transform.flatten_recurse(meta_items))):
            print('\nThese are used primarily for branding (with the '
                  'exception of recursion level, which is used '
                  'operationally).\n*All* items are REQUIRED (and if any are '
                  'blank or invalid, the entire section will restart), but '
                  'you may want to tweak the VERSION_INFO.txt.j2 template if '
                  'you don\'t want this information exposed to your users '
                  '(see the manual for more detail).')
            print('\n++ META ITEMS || NAMES ++')
            # https://en.wikipedia.org/wiki/8.3_filename
            meta_items['names']['name'] = transform.sanitize_input(
                                            input(
                '\nWhat 8.3 filename should be used as the name of this '
                'project/live distro? Refer to the manual\'s Configuration '
                'section for path /bdisk/profile/meta/names/name for '
                'restrictions (there are quite a few).\n8.3 Name: ').strip(),
                                            no_underscores = True).upper()
            if (len(meta_items['names']['name']) > 8) or (
                                    meta_items['names']['name'] == ''):
                print('Invalid; skipping...')
                meta_items['names']['name'] = None
            # Note: 2009 spec
            # http://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap03.html#tag_03_282
            meta_items['names']['uxname'] = input(
                '\nWhat name should be used as the "human-readable" name of '
                'this project/live distro? Refer to the manual\'s '
                'Configuration section for path '
                '/bdisk/profile/meta/names/uxname for restrictions, but in a '
                'nutshell it must be compatible with the "POSIX Portable '
                'Filename Character Set" specification (the manual has a '
                'link).\nName: ').strip()
            if not valid.posix_filename(meta_items['names']['uxname']):
                print('Invalid; skipping...')
                meta_items['names']['uxname'] = None
            meta_items['names']['pname'] = input(
                '\nWhat name should be used as the "pretty" name of this '
                'project/live distro? Refer to the manual\'s Configuration '
                'section for path /bdisk/profile/meta/names/uxname for '
                'restrictions, but this is by far the most lax naming. It '
                'should be used for your actual branding.\nName: ').strip()
            if meta_items['names']['pname'] == '':
                meta_items['names']['pname'] = None
            print('\n++ META ITEMS || PROJECT INFORMATION ++')
            meta_items['uri'] = input('\nWhat is your project\'s URI/URL?'
                                      '\nURL: ').strip()
            if not valid.url(meta_items['uri']):
                print('Invalid; skipping...')
                meta_items['uri'] = None
            meta_items['ver'] = input(
                '\nWhat version is this project? It follows the same rules as '
                'the POSIX filename specification mentioned earlier (as we '
                'use it to name certain files).\nVersion: ')
            while not meta_items['desc']:
                print('\nWhat is your project\'s description?'
                      '\nAccepts multiple lines, etc.'
                      '\nPress CTRL-d (on *nix/macOS) or CTRL-z (on Windows) '
                      'on an empty line when done.'
                      '\nIt will be echoed back for confirmation after it is '
                      'entered (with the option to re-enter if '
                      'desired/needed - this will NOT restart the entire Meta '
                      'section).')
                meta_items['desc'] = prompt.multiline_input(
                                                    prompt = '\nDescription: ')
                print('-----\n{0}\n-----'.format(meta_items['desc']))
                _confirm = prompt.confirm_or_no(
                                            prompt = 'Does this look okay?\n')
                if not _confirm:
                    meta_items['desc'] = None
            print('\n++ META ITEMS || DEVELOPER INFORMATION ++')
            meta_items['dev']['author'] = (input(
                '\nWhat is YOUR name?\nName: ')).strip()
            meta_items['dev']['email'] = (input('\nWhat is your email address?'
                                                '\nemail: ')).strip()
            if not valid.email(meta_items['dev']['email']):
                print('Invalid; skipping...')
                meta_items['dev']['email'] = None
            meta_items['dev']['website'] = (input('\nWhat is your website?\n'
                                                  'Website: ')).strip()
            if not valid.url(meta_items['dev']['website']):
                print('Invalid; skipping...')
                meta_items['dev']['website'] = None
            print('\n++ META ITEMS || OPERATIONAL CONFIGURATION ++')
            meta_items['max_recurse'] = transform.sanitize_input(input(
                '\nAs of the 4.x branch, BDisk configuration files support '
                'cross-document substitution via XPath references, even '
                'recursively. How many levels of recursion do you want this '
                'profile to support? Note that the default limit for Python '
                'is 1000 (and CAN be changed, but is not recommended) and '
                'each level of recursion you add can POTENTIALLY add '
                'additional CPU/RAM strain. HOWEVER, chances are if your '
                'machine\'s good enough to run BDisk, it\'s good enough for '
                'whatever you set. I recommend setting it to 5, because any '
                'more than that and your configuration becomes cumbersome to '
                'maintain.\nMax recursion: ').strip())
            if not valid.integer(meta_items['max_recurse']):
                print('Invalid; skipping...')
                meta_items['dev']['website'] = None
        meta = lxml.etree.SubElement(self.profile, 'meta')
        for e in meta_items:
            elem = lxml.etree.SubElement(meta, e)
            # These have nested items.
            if isinstance(meta_items[e], dict):
                for s in meta_items[e]:
                    subelem = lxml.etree.SubElement(elem, s)
                    subelem.text = meta_items[e][s]
            else:
                elem.text = meta_items[e]
        print()
        return()

    def get_accounts(self):
        print('\n++ ACCOUNTS ++')
        accounts = lxml.etree.SubElement(self.profile, 'accounts')
        pass_attribs = ('hashed', 'hash_algo', 'salt')
        rootpass = None
        print('\n++ ACCOUNTS || ROOT ++')
        if not rootpass:
            prompt_attribs = pass_prompt('root')
            rootpass = lxml.etree.Element('rootpass')
            for i in pass_attribs:
                rootpass.attrib[i] = transform.py2xml(prompt_attribs[i])
            rootpass.text = prompt_attribs['password']
        accounts.append(rootpass)
        print('\n++ ACCOUNTS || USERS ++')
        more_accounts = prompt.confirm_or_no(prompt = ('\nWould you like to '
                                'add a non-root/regular user?\n'),
                                usage = ('{0} for yes, {1} for no...\n'))
        users = lxml.etree.SubElement(accounts, 'users')
        while more_accounts:
            user = None
            _user_invalid = True
            _user_text = {'username': None,
                          'password': None,
                          'comment': None}
            while _user_invalid:
                _username = (input('\nWhat should the username be?'
                                   '\nUsername: ')).strip()
                if not valid.username(_username):
                    print('\nThat username string is invalid. Consult the '
                          'manual and the man page for useradd(8). Let\'s '
                          'have another go.')
                else:
                    _user_text['username'] = _username
                    _user_invalid = False
            _sudo = prompt.confirm_or_no(prompt = ('\nGive {0} full sudo '
                                         'access?\n').format(_username))
            _pass_attr = pass_prompt(_username)
            _user_text['password'] = _pass_attr['password']
            _user_text['comment'] = transform.no_newlines(
                (input('\nWhat do you want the GECOS comment to be? This is '
                       'USUALLY the full "real" name of the user (or a '
                       'description of the service, etc.). You can leave it '
                       'blank if you want.\nGECOS: ')).strip())
            user = lxml.etree.Element('user')
            user.attrib['sudo'] = transform.py2xml(_sudo)
            _elems = {}
            for elem in _user_text:
                _elems[elem] = lxml.etree.SubElement(user, elem)
                _elems[elem].text = _user_text[elem]
            for i in pass_attribs:
                _elems['password'].attrib[i] = transform.py2xml(_pass_attr[i])
            users.append(user)
            more_accounts = prompt.confirm_or_no(prompt = ('\nWould you like '
                                                    'to add another user?\n'),
                                                usage = ('{0} for yes, {1} '
                                                         'for no...\n'))
        return()

    def get_sources(self):
        print('\n++ SOURCES ++')
        sources = lxml.etree.SubElement(self.profile, 'sources')
        more_sources = True
        _arches = []
        _supported_arches = {'x86': ('(Also referred to by distros as "i386", '
                                     '"i486", "i686", and "32-bit")'),
                             'x86_64': ('(Also referred to by distros as '
                                        '"64-bit")')}
        while more_sources:
            # this doesn't trigger? maybe?
            if len(_arches) >= len(_supported_arches):
                # All supported arches have been added. We currently don't
                # support mirror-balancing. TODO?
                print('\nCannot add more sources; all supported architectures '
                      'have been used. Moving on.')
                more_sources = False
                break
            if len(_arches) > 0:
                print('\n\t(Currently added arches: {0})'.format(
                                                        ', '.join(_arches)))
            _print_arches = '\n\t'.join(
                ['{0}:\t{1}'.format(*i) for i in _supported_arches.items()])
            source = lxml.etree.Element('source')
            arch = (input((
                '\nWhat hardware architecture is this source for?\n(Note: '
                'BDisk currently only supports the listed architectures).\n'
                '\n\t{0}\n\nArch: ').format(_print_arches))).strip().lower()
            if arch not in _supported_arches.keys():
                print('That is not a supported architecture. Trying again.')
                continue
            source.attrib['arch'] = arch
            print('\n++ SOURCES || {0} ++'.format(arch.upper()))
            print('\n++ SOURCES || {0} || TARBALL ++'.format(arch.upper()))
            tarball = (input('\nWhat URL should be used for the tarball? '
                              '(Note that this is ONLY tested for syntax, we '
                              'don\'t confirm it\'s downloadable when running '
                              'through the configuration generator wizard - '
                              'so please make sure you enter the correct URL!)'
                              '\nTarball: ')).strip()
            if not valid.url(tarball):
                print('That isn\'t a valid URL. Please double-check and try '
                      'again.')
                continue
            tarball = transform.url_to_dict(tarball, no_None = True)
            tarball_elem = lxml.etree.SubElement(source, 'tarball')
            tarball_elem.attrib['flags'] = 'latest'
            tarball_elem.text = tarball['full_url']
            print('\n++ SOURCES || {0} || CHECKSUM ++'.format(arch.upper()))
            # TODO: explicit not being set for explicitly-set sums,
            # and checksum string not actually added to those. investigate.
            chksum = lxml.etree.SubElement(source, 'checksum')
            _chksum_chk = prompt.confirm_or_no(prompt = (
                '\nWould you like to add a checksum for the tarball? (BDisk '
                'can fetch a checksum file from a remote URL at build-time or '
                'you can hardcode an explicit checksum in.)\n'),
                                               usage = ('{0} for yes, {1} '
                                                        'for no...\n'))
            if not _chksum_chk:
                checksum = None
            else:
                checksum = (input(
                    '\nPlease enter the URL to the checksum file OR the '
                    'explicit checksum you wish to use.\nChecksum (remote URL '
                    'or checksum hash): ')).strip()
                if valid.url(checksum):
                    checksum = transform.url_to_dict(checksum)
                    checksum_type = prompt.hash_select(prompt = (
                        '\nPlease select the digest type (by number) of the '
                        'checksums contained in this file.\n'
                        'Can be one of:\n\n\t{0}'
                        '\n\nChecksum type: '))
                    if checksum_type is False:
                        print('Select by NUMBER. Starting over.')
                        continue
                    elif checksum_type is None:
                        print('Invalid selection. Starting over.')
                        continue
                    chksum.attrib['hash_algo'] = checksum_type
                    chksum.attrib['explicit'] = "no"
                    chksum.text = checksum['full_url']
                else:
                    # Maybe it's a digest string.
                    checksum_type = detect.any_hash(checksum)
                    if not checksum_type:
                        print('\nCould not detect which hash type this digest '
                              'is.')
                        checksum_type = prompt.hash_select(
                            prompt = ('\nPlease select from the following '
                                      'list (by numer):\n\n\t{0}'
                                      '\n\nChecksum type: '))
                        if checksum_type is False:
                            print('Select by NUMBER. Starting over.')
                            continue
                        elif checksum_type is None:
                            print('Invalid selection. Starting over.')
                            continue
                    elif len(checksum_type) > 1:
                        checksum_type = prompt.hash_select(
                            prompt = (
                            '\nWe found several algorithms that can match '
                            'your provided digest.\nPlease select the '
                            'appropriate digest method from the list below '
                            '(by number):\n\n\t{0}\n\nChecksum type: '))
                        if checksum_type is False:
                            print('Select by NUMBER. Starting over.')
                            continue
                        elif checksum_type is None:
                            print('Invalid selection. Starting over.')
                            continue
                    else:
                        checksum_type = checksum_type[0]
                        chksum.attrib['explicit'] = "yes"
                        chksum.text = checksum
                    chksum.attrib['hash_algo'] = checksum_type
            print('\n++ SOURCES || {0} || GPG ++'.format(arch.upper()))
            sig = lxml.etree.SubElement(source, 'sig')
            _gpg_chk = prompt.confirm_or_no(prompt = (
                '\nWould you like to add a GPG(/GnuPG/PGP) signature for the '
                'tarball?\n'))
            if _gpg_chk:
                gpgsig = (input(
                    '\nPlease enter the remote URL for the GPG signature '
                    'file.\nGPG Signature File URL: ')
                         ).strip()
                if not valid.url(gpgsig):
                    print('Invalid URL. Starting over.')
                    continue
                else:
                    gpgsig = transform.url_to_dict(gpgsig)
                    sig.text = gpgsig['full_url']
                sigkeys = prompt.confirm_or_no(prompt = (
                    '\nDo you know the key ID of the authorized/valid '
                    'signer? (If not, we will fetch the GPG signature file '
                    'now and try to parse it for key IDs.)\n'),
                                              usage = ('{0} for yes, {1} '
                                                       'for no...\n'))
                if sigkeys:
                    sigkeys = (input('\nWhat is the key ID? You can use the '
                                    'fingerprint, full 40-character key ID '
                                    '(preferred), 16-character "long" ID, or '
                                    'the 8-character "short" ID '
                                    '(HIGHLY unrecommended!).\nKey ID: ')
                             ).strip().upper()
                    if not valid.gpgkeyID(sigkeys):
                        print('That is not a valid GPG key ID. Restarting')
                        continue
                    sig.attrib['keys'] = sigkeys
                else:
                    sigkeys = detect.gpgkeyID_from_url(gpgsig['full_url'])
                    if not isinstance(sigkeys, list):
                        print('Could not properly parse any keys in the '
                              'signature file. Restarting.')
                        continue
                    elif len(sigkeys) == 0:
                        print('We didn\'t find any key IDs embedded in the '
                              'given signature file. Restarting.')
                        continue
                    elif len(sigkeys) == 1:
                        _s = 'Does this key'
                    else:
                        _s = 'Do these keys'
                    _key_info = [detect.gpgkey_info(k) for k in sigkeys]
                    print('\nWe found the following key ID information:\n\n')
                    for _key in _key_info:
                        print('\t{0}\n'.format(_key['Full key']))
                        for _uid in _key['User IDs']:
                            # COULD flatten this to just one level.
                            print('\t\t{0}'.format(_uid['Name']))
                            for k in _uid:
                                if k != 'Name':
                                    print('\t\t\t{0:<9} {1}'.format(
                                            '{0}:'.format(k), _uid[k]))
                    _key_chk = prompt.confirm_or_no(prompt = (
                        '\n{0} look correct?\n').format(_s))
                    if not _key_chk:
                        print('Something must have gotten futzed, then.'
                              'Restarting!')
                        continue
                    sig.attrib['keys'] = ','.join(sigkeys)
            elems = {}
            for s in ('mirror', 'webroot'):
                elems[s] = lxml.etree.SubElement(source, s)
            elems['mirror'].text = '{scheme}://{host}'.format(**tarball)
            if tarball['port'] != '':
                elems['mirror'].text += ':{0}'.format(tarball['port'])
            elems['webroot'].text = '{path}'.format(**tarball)
            sources.append(source)
            _arches.append(arch)
            more_sources = prompt.confirm_or_no(prompt = ('\nWould you like '
                                                          'to add another '
                                                          'source?\n'),
                                                usage = ('{0} for yes, {1} '
                                                         'for no...\n'))
        return()
    
    def get_build(self):
        print('\n++ BUILD ++')
        build = lxml.etree.SubElement(self.profile, 'build')
        _chk_optimizations = prompt.confirm_or_no(prompt = (
            '\nWould you like to enable experimental optimizations?\n'),
                                                usage = (
                                '{0} for yes, {1} for no...\n'))
        if _chk_optimizations:
            build.attrib['its_full_of_stars'] = 'yes'
        print('\n++ BUILD || PATHS ++')
        # Thankfully, we can simplify a lot of this.
        _dir_strings = {'base': ('the base directory (used for files that are '
                                 'required for basic guest environment '
                                 'support)'),
                        'cache': ('the caching directory (used for temporary '
                                  'files, temporary downloads, etc.)'),
                        'chroot': ('the chroot directory (where we store '
                                   'the root filesystems that are converted '
                                   'into the live environment'),
                        'overlay': ('the overlay directory (allowing for '
                                    'injecting files into the live '
                                    'environment\'s filesystem)'),
                        'templates': ('the template directory (for templating '
                                      'configuration files in the live '
                                      'environment)'),
                        'mount': ('the mount directory (where chroots are '
                                  'mounted to perform preparation tasks)'),
                        'distros': ('the distro plugin directory (where '
                                    'plugins supporting other guest Linux '
                                    'distributions are put)'),
                        'dest': ('the destination directory (where finished '
                                 'products like ISO image files go)'),
                        'iso': ('the iso directory (the overlay directory for '
                                'the "outer" layer of media)'),
                        'http': ('the HTTP directory (where a webroot is '
                                 'created that can be used to serve iPXE)'),
                        'tftp': ('the TFTP directory (where a TFTP/'
                                 'traditional PXE root is created)'),
                        'pki': ('the SSL/TLS PKI directory (where we store '
                                'the PKI structure we use/re-use - MAKE SURE '
                                'it is in a path that is well-protected!)')}
        has_paths = False
        # Get the paths
        while not has_paths:
            paths = lxml.etree.Element('paths')
            _paths_elems = {}
            for _dir in _dir_strings:
                _paths_elems[_dir] = lxml.etree.SubElement(paths, _dir)
                path = prompt.path(_dir_strings[_dir])
                _paths_elems[_dir].text = path
            build.append(paths)
            has_paths = True
        print('\n++ BUILD || ENVIRONMENT DISTRO ++')
        has_distro = False
        while not has_distro:
            try:
                distro_path = self.profile.xpath('//paths/distros/text()')[0]
            except IndexError:
                distro_path = 'your "distros" path'
            distro = (input(('\nWhich distro plugin/distro base are you '
                             'using? See the manual for more information. A '
                             'matching plugin MUST exist in {0} for a build '
                             'to complete successfully! The default (Arch '
                             'Linux, "archlinux") will be used if left blank.'
                             '\nDistro base: ').format(distro_path))).strip()
            if distro == '':
                distro = 'archlinux'
            if not valid.plugin_name(distro):
                print('That is not a valid name. See the manual for examples '
                      'and shipped plugins. Retrying.')
                continue
            else:
                has_distro = True
            distro_elem = lxml.etree.SubElement(build, 'distro')
            distro_elem.text = distro
        return()
    
    def get_iso(self):
        print('\n++ ISO ++')
        # We don't need to ask if it's multiarch if we only have one arch.
        iso = lxml.etree.Element('iso')
        _arches = []
        for _source in self.profile.xpath('sources/source'):
            _arches.append(_source.attrib['arch'])
        if len(_arches) < 2:
            iso.attrib['multi_arch'] = _arches[0]
            self.profile.append(iso)
        # We have more than one arch, so we need to ask how they want to handle
        # it.
        _ma_strings = {'yes': ('a multi-arch ISO (both architectures on one '
                               'ISO)'),
                       'no': ('separate image files for '
                              '{0}').format(' and '.join(_arches))}
        for a in _arches:
            _ma_strings[a] = 'only build an image file for {0}'.format(a)
        if len(_arches) > 1:
            _multi_arch_input = None
            while not _multi_arch_input:
                print('\n++ ISO || MULTI-ARCH ++')
                _multi_arch = (input((
                    '\nYou have defined mutliple architecture sources. BDisk '
                    'allows you to build an ISO image (USB image, etc.) that '
                    'will support both architectures using the same file. '
                    'Please consult the manual if you need further '
                    'information.\nPossible values:\n'
                    '\n\t{0}\n\nMulti-arch: ').format(
                    '\n\t'.join(
                    ['{0}:\t{1}'.format(k, v) for k, v in _ma_strings.items()]
                        )))).strip().lower()
                if _multi_arch not in _ma_strings.keys():
                    print('Invalid selection; retrying.')
                    continue
                else:
                    _multi_arch_input = _multi_arch
            iso.attrib['multi_arch'] = _multi_arch_input
        _gpg_sign = None
        while not _gpg_sign:
            print('\n++ ISO || SIGNING ++')
            _gpg_input = prompt.confirm_or_no(prompt = (
                '\nWe can sign ISO image files using GPG (we\'ll give the '
                'option to configure it a bit later).\nWould you like to sign '
                'the ISO/USB image files with GPG?\n'), usage = (
                                '{0} for yes, {1} for no...\n'))
            _gpg_sign = ('yes' if _gpg_input else 'no')
        iso.attrib['sign'] = _gpg_sign
        self.profile.append(iso)
        return()
    
    def get_ipxe(self):
        print('\n++ iPXE ++')
        ipxe = lxml.etree.Element('ipxe')
        _ipxe = None
        while not _ipxe:
            _ipxe = prompt.confirm_or_no(prompt = (
                '\nBDisk has built-in support for iPXE (https://ipxe.org/, '
                'see the manual for more information). Would you like to '
                'build iPXE support?\n'), usage = (
                                '{0} for yes, {1} for no...\n'))
            _ipxe = ('yes' if _ipxe else 'no')
        if _ipxe == 'yes':
            print('\n++ iPXE || MINI-ISO ++')
            _iso = prompt.confirm_or_no(prompt = (
                '\nWould you like to build a "mini-ISO" (see the manual) for '
                'bootstrapping iPXE booting from USB or optical media?\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
            ipxe.attrib['iso'] = ('yes' if _iso else 'no')
            print('\n++ iPXE || SIGNING ++')
            _sign = prompt.confirm_or_no(prompt = (
                '\nBDisk can sign the mini-ISO and other relevant files for '
                'iPXE builds using GPG. Would you like to sign the iPXE build '
                'distributables? (You\'ll have the chance to configure GPG '
                'later).\n'), usage = ('{0} for yes, {1} for no...\n'))
            ipxe.attrib['sign'] = ('yes' if _sign else 'no')
            _uri = None
            while not _uri:
                print('\n++ iPXE || URL ++')
                _uri = (input(
                    '\niPXE uses a remote URI to boot. What URI should this '
                    'profile\'s iPXE use? (Consult the manual for more '
                    'information.)\niPXE Boot URL: ')).strip()
                if not valid.url(_uri):
                    print('Invalid URL, retrying...')
                    _uri = None
                    continue
                else:
                    uri = lxml.etree.SubElement(ipxe, 'uri')
                    uri.text = _uri
        if _ipxe == 'yes':
            self.profile.append(ipxe)
        return()
    
    def get_pki(self):
        print('\n++ SSL/TLS PKI ++')
        pki = lxml.etree.Element('pki')
        _pki = None
        while not _pki:
            _pki = prompt.confirm_or_no(prompt = (
                '\nWould you like to support SSL/TLS transport for various '
                'functions? Currently this is only used for iPXE, but future '
                'applications may be possible.\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
        if _pki:
            _pki_url_chk = self.profile.xpath('ipxe/uri/text()')
            _pki_url = (_pki_url_chk[0] if _pki_url_chk else None)
            print('\n++ SSL/TLS PKI || OVERWRITE ++')
            _overwrite = prompt.confirm_or_no(prompt = (
                '\nYou\'ll have the opportunity in a moment to configure '
                'paths for the various files, but do you want BDisk to '
                're-generate (and thus overwrite) any of the files it finds? '
                'If you use these files for anything OTHER than BDisk (or '
                'wish to keep persistent keys and certs), you should '
                'DEFINITELY answer no here.\n'),
                    usage = ('{0} for yes, {1} for no...\n'))
            pki.attrib['overwrite'] = ('yes' if _overwrite else 'no')
            for x in ('ca', 'client'):
                print('\n++ SSL/TLS PKI || {0} ++'.format(x.upper()))
                _x = None
                while not _x:
                    _x = prompt.ssl_object(x, _pki_url)
                elem = lxml.etree.SubElement(pki, x)
                _elems = {}
                for e in _x['paths']:
                    _elems[e] = lxml.etree.SubElement(elem, e)
                    _elems[e].text = _x['paths'][e]
                for e in _x['attribs']:
                    for a in _x['attribs'][e]:
                        _elems[e].attrib[a] = _x['attribs'][e][a]
        if _pki:
            self.profile.append(pki)
        return()

    def get_gpg(self):
        _sigchk = False
        _xpaths = ['//iso/@sign', '//ipxe/@sign']
        for x in _xpaths:
            _x = self.profile.xpath(x)
            for a in _x:
                if a == 'yes':
                    _sigchk = True
                    break
            if _sigchk:
                break
        if not _sigchk:
            # An empty gpg element signifies a blank configuration.
            lxml.etree.SubElement(self.profile, 'gpg')
            return()
        gpg = lxml.etree.Element('gpg')
        print('\n++ GPG ++')
        _gpg = None
        while not _gpg:
            print('\n++ GPG || KEY ID ++')
            _gpg = (input('\nYou have specified GPG signing for one or more '
                          'components. If you have a key already, please '
                          'enter the key ID here; otherwise if left blank, '
                          'BDisk will generate one for you.\n'
                          'Key ID: ')).upper().strip()
            if _gpg == '':
                _gpg = 'none'
            else:
                if not valid.gpgkeyID(_gpg):
                    print('That is not a valid GPG key ID. Retrying.')
                    continue
        gpg.attrib['keyid'] = _gpg
        print('\n++ GPG || GPG HOME DIRECTORY ++')
        _gpghome = None
        while not _gpghome:
            _gpghome = (input('\nWhat directory should be used for the GnuPG '
                              'home directory? If left blank, BDisk will use '
                              'the system default (first checking for an '
                              'environment variable called GNUPGHOME, and '
                              'then trying the built-in ~/.gnupg directory).'
                              '\nGPG Home Directory: '))
            if _gpghome.strip() != '':
                gpg.attrib['gnupghome'] = _gpghome
            else:
                _gpghome = 'none'
        print('\n++ GPG || KEYSERVER PUSHING ++')
        _gpgpublish = prompt.confirm_or_no(prompt = (
            '\nWould you like to push the key to the SKS keyserver pool '
            '(making it much easier for end-users to look it up)?\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
        gpg.attrib['publish'] = ('yes' if _gpgpublish else 'no')
        print('\n++ GPG || PASSWORD HANDLING ++')
        _gpgpass_prompt = prompt.confirm_or_no(prompt = (
            '\nWould you like BDisk to prompt you for a passphrase? If not, '
            'you\'ll either have to include the passphrase in plaintext in '
            'the configuration (HIGHLY unrecommended) or use a blank '
            'passphrase (also HIGHLY unrecommended).\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
        gpg.attrib['prompt_passphrase'] = ('yes' if _gpgpass_prompt else 'no')
        _pass = None
        if not _gpgpass_prompt:
            while not _pass:
                print('\n++ GPG || PASSPHRASE ++')
                _pass = getpass.getpass((
                    '\nYou have specified not to use passphrase prompting for '
                    'GPG. As such, you will need to provide the passphrase. '
                    'If left blank, BDisk will assume one is not/should not '
                    'be set.\nPassphrase (will NOT echo back; type '
                    'carefully!): '))
                if _pass.strip()  == '':
                    _pass = 'none'
                elif not valid.password(_pass):
                    print('As a safety precaution, we are refusing to use '
                          'this password. It should entirely consist of the '
                          '95 printable ASCII characters. Consult the '
                          'manual\'s section on passwords for more '
                          'information.\nLet\'s try this again, shall we?')
                    _pass = None
                    continue
                else:
                    gpg.attrib['passphrase'] = _pass
        if gpg.attrib['keyid'] == 'none':
            _more_subkeys = True
            while _more_subkeys:
                _subkey = prompt.gpg_keygen_attribs()
                subkey = lxml.etree.SubElement(gpg, 'key')
                for a in _subkey['attribs']:
                    subkey.attrib[a] = _subkey['attribs'][a]
                for e in _subkey['params']:
                    param = lxml.etree.SubElement(subkey, e)
                    param.text = _subkey['params'][e]
                _more_subkeys = prompt.confirm_or_no(prompt = (
                    '\nDo you want to add another subkey?\n'),
                    usage = ('{0} for yes, {1} for no...\n'))
        self.profile.append(gpg)
        return()

    def get_sync(self):
        print('\n++ SYNC ++')
        print('This section will allow you to configure REMOTE paths to copy '
              'the finished products to. These are COPIES, meaning they will '
              'exist in the destination paths you specified earlier but will '
              'also be copied to these destinations. The difference is these '
              'can be on a remote host and will be copied via rsync.')
        _sync_chk = prompt.confirm_or_no(prompt = (
                        '\nWould you like to enable remote syncing?\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
        if not _sync_chk:
            elem = lxml.etree.SubElement(self.profile, 'sync')
            rsync = lxml.etree.SubElement(elem, 'rsync')
            rsync.attrib['enabled'] = 'no'
            return()
        sync = lxml.etree.Element('sync')
        _syncs = {'ipxe': ('the iPXE base'),
                  'tftp': ('the TFTP root'),
                  'iso': ('the ISO images destination'),
                  'gpg': ('the exported GPG public key')}
        for s in _syncs:
            print('\n++ SYNC || {0} ++'.format(s.upper()))
            _item_sync_chk = prompt.confirm_or_no(prompt = (
                        '\nWould you like to sync {0}?\n'.format(_syncs[s])),
                                    usage = ('{0} for yes, {1} for no...\n'))
            elem = lxml.etree.SubElement(sync, s)
            elem.attrib['enabled'] = ('yes' if _item_sync_chk else 'no')
            if not _item_sync_chk:
                continue
            if s == 'gpg':
                _choices = ['ASCII', 'binary']
                _export_type = (input(
                        ('\nWhat type of export dump would you like to use '
                         'for the GPG public key? (You can use the first '
                         'letter only as an abbreviation; the default is '
                         'ASCII.)\n'
                         'Choices:\n\n\t{0}\n\nExport type: ').format(
                                '\n\t'.join(_choices)
                                ))).strip().lower()
                if _export_type.startswith('a'):
                    _export_type = 'asc'
                elif _export_type.startswith('b'):
                    _export_type = 'bin'
                else:
                    print('Using the default.')
                    _export_type = 'asc'
                elem.attrib['format'] = _export_type
            _path = None
            while not _path:
                _path = input(
                    ('\nWhere (remote path) would you like {0} to be synced?\n'
                     'Path: ').format(_syncs[s]))
                if _path.strip() == '':
                    print('Please specify a path. Retrying...')
                    _path = None
                    continue
                elem.text = _path
        rsync = lxml.etree.SubElement(sync, 'rsync')
        print('\n++ SYNC || RSYNC ++')
        _rsync = prompt.confirm_or_no(prompt = (
            '\nEnable rsync? If disabled, no syncing would be done even if '
            'enabled by a specific item above.\n'),
                                    usage = ('{0} for yes, {1} for no...\n'))
        if not _rsync:
            self.profile.append(sync)
            return()
        _host = (input(
                    '\nWhat host should we use for rsync?\nHost: ')
                ).strip().lower()
        if ':' in _host:
            _h = _host.split(':')
            _host = _h[0]
            _port = _h[1]
        else:
            _port = None
        host = lxml.etree.SubElement(rsync, 'host')
        host.text = _host
        while not _port:
            _port = (input(
                        '\nWhat port should we use? (Default: 22)\nPort: ')
                    ).strip()
            if _port == '':
                _port = '22'
            if not valid.integer(_port):
                print('Invalid port number; try again.')
                _port = None
                continue
        port = lxml.etree.SubElement(rsync, 'port')
        port.text = _port
        _user = (input(
                    '\nWhat user should we use for {0}?\nUser: '.format(_host)
                )).strip()
        while not valid.username(_user):
            print('Invalid username.')
            _user = (input('\nUsername: ')).strip()
        user = lxml.etree.SubElement(rsync, 'user')
        user.text = _user
        _pubkey = input('\nWhat path should we use for the SSH private key? '
                        'Default: ~/.ssh/id_rsa\n'
                        'Key path: ')
        pubkey = lxml.etree.SubElement(rsync, 'pubkey')
        pubkey.text = _pubkey
        self.profile.append(sync)
        return()

def main():
    cg = ConfGenerator()
    cg.main()
    print()
    print(lxml.etree.tostring(cg.cfg,
                              pretty_print = True,
                              encoding = 'UTF-8',
                              xml_declaration = True
                             ).decode('utf-8'))

if __name__ == '__main__':
    main()
