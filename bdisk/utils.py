import _io
import copy
import crypt
import GPG
import getpass
import hashid
import hashlib
import iso3166
import os
import pprint
import prompt_strings
import re
import string
import uuid
import validators
import zlib
import lxml.etree
from bs4 import BeautifulSoup
from collections import OrderedDict
from dns import resolver
from email.utils import parseaddr as emailparse
from passlib.context import CryptContext as cryptctx
from urllib.parse import urlparse
from urllib.request import urlopen

# Supported by all versions of GNU/Linux shadow
passlib_schemes = ['des_crypt', 'md5_crypt', 'sha256_crypt', 'sha512_crypt']

# Build various hash digest name lists
digest_schemes = list(hashlib.algorithms_available)
# Provided by zlib
# TODO
digest_schemes.append('adler32')
digest_schemes.append('crc32')

crypt_map = {'sha512': crypt.METHOD_SHA512,
             'sha256': crypt.METHOD_SHA256,
             'md5': crypt.METHOD_MD5,
             'des': crypt.METHOD_CRYPT}

class XPathFmt(string.Formatter):
    def get_field(self, field_name, args, kwargs):
        vals = self.get_value(field_name, args, kwargs), field_name
        if not vals[0]:
            vals = ('{{{0}}}'.format(vals[1]), vals[1])
        return(vals)

class detect(object):
    def __init__(self):
        pass

    def any_hash(self, hash_str):
        h = hashid.HashID()
        hashes = []
        for i in h.identifyHash(hash_str):
            if i.extended:
                continue
            x = i.name
            if x.lower() in ('crc-32', 'ripemd-160', 'sha-1', 'sha-224',
                             'sha-256', 'sha-384', 'sha-512'):
                # Gorram you, c0re.
                x = re.sub('-', '', x.lower())
            _hashes = [h.lower() for h in digest_schemes]
            if x.lower() in sorted(list(set(_hashes))):
                hashes.append(x)
        return(hashes)

    def password_hash(self, passwd_hash):
        _ctx = cryptctx(schemes = passlib_schemes)
        algo = _ctx.identify(passwd_hash)
        if algo:
            return(re.sub('_crypt$', '', algo))
        else:
            return(None)
        return()

    def password_hash_salt(self, salted_hash):
        _hash_list = salted_hash.split('$')
        salt = _hash_list[2]
        return(salt)

    def remote_files(self, url_base, ptrn = None, flags = []):
        with urlopen(url_base) as u:
            soup = BeautifulSoup(u.read(), 'lxml')
        urls = []
        if 'regex' in flags:
            if not isinstance(ptrn, str):
                raise ValueError('"ptrn" must be a regex pattern to match '
                                 'against')
            else:
                ptrn = re.compile(ptrn)
        for u in soup.find_all('a'):
            if not u.has_attr('href'):
                continue
            if 'regex' in flags:
                if not ptrn.search(u.attrs['href']):
                    continue
            if u.has_attr('href'):
                urls.append(u.attrs['href'])
        if not urls:
            return(None)
        # We certainly can't intelligently parse the printed timestamp since it
        # varies so much and that'd be a nightmare to get consistent...
        # But we CAN sort by filename.
        if 'latest' in flags:
            urls = sorted(list(set(urls)))
            urls = urls[-1]
        else:
            urls = urls[0]
        return(urls)

    def gpgkeyID_from_url(self, url):
        with urlopen(url) as u:
            data = u.read()
        g = GPG.GPGHandler()
        key_ids = g.get_sigs(data)
        del(g)
        return(key_ids)

    def gpgkey_info(self, keyID, secret = False):
        def _get_key():
            key = None
            try:
                key = g.ctx.get_key(keyID, secret = secret)
            except GPG.gpg.errors.KeyNotFound:
                return(None)
            except Exception:
                return(False)
            return(key)
        uids = {}
        g = GPG.GPGHandler()
        _orig_kl_mode = g.ctx.get_keylist_mode()
        if _orig_kl_mode != GPG.gpg.constants.KEYLIST_MODE_EXTERN:
            _key = _get_key()
            if not _key:
                g.ctx.set_keylist_mode(GPG.gpg.constants.KEYLIST_MODE_EXTERN)
                _key = _get_key()
        else:
            _key = _get_key()
        if not _key:
            g.ctx.set_keylist_mode(_orig_kl_mode)
            del(g)
            return(None)
        else:
            uids['Full key'] = _key.fpr
            uids['User IDs'] = []
            for _uid in _key.uids:
                _u = OrderedDict()
                # Strings
                for attr in ['Name', 'Email', 'Comment']:
                    s = getattr(_uid, attr.lower())
                    if s and s != '':
                        _u[attr] = s
                # Key attributes
                _u['Invalid'] = (True if _uid.invalid else False)
                _u['Revoked'] = (True if _uid.revoked else False)
                uids['User IDs'].append(_u)
        g.ctx.set_keylist_mode(_orig_kl_mode)
        del(g)
        return(uids)

    def supported_hashlib_name(self, name):
        # Get any easy ones out of the way first.
        if name in digest_schemes:
            return(name)
        # Otherwise grab the first one that matches, in order from the .
        _digest_re = re.compile('^{0}$'.format(name.strip()), re.IGNORECASE)
        for h in digest_schemes:
            if _digest_re.search(h):
                return(h)
        return(None)

class generate(object):
    def __init__(self):
        pass

    def hash_password(self, password, salt = None, algo = crypt.METHOD_SHA512):
        if not salt or salt == 'auto':
            _salt = crypt.mksalt(algo)
        else:
            _salt = salt
        if not password:
            # Intentionally empty password.
            return('')
        return(crypt.crypt(password, _salt))

    def hashlib_names(self):
        hashes = []
        for h in sorted(digest_schemes):
            r = re.compile('^{0}$'.format(h), re.IGNORECASE)
            if len([i for i in filter(r.search, hashes)]) == 0:
                hashes.append(h)
        return(hashes)

    def salt(self, algo = None):
        if not algo:
            algo = 'sha512'
        algo = crypt_map[algo]
        return(crypt.mksalt(algo))

class prompts(object):
    def __init__(self):
        self.promptstr = prompt_strings.PromptStrings()

    # TODO: these strings should be indexed in a separate module and
    # sourced/imported. we should generally just find a cleaner way to do this.

    def confirm_or_no(self, prompt = '', invert = False,
                      usage = '{0} to confirm, otherwise {1}...\n'):
        # A simplified version of multiline_input(), really.
        # By default, Enter confirms (and returns True) and CTRL-d returns
        # False unless - you guessed it - invert is True.
        # usage is a string appended to prompt that explains which keys to use.
        # It accepts two strformats: 0 is the EOF keystroke, and 1 is the Enter
        # key (those are flipped if invert = True).
        _enter_ks = 'Enter/Return'
        if os.name == 'posix':
            _ks = 'CTRL-d'
        else:  # What does os.name == "java" use?
            _ks = 'CTRL-z'
        if invert:
            _usage = usage.format(_ks, _enter_ks)
        else:
            _usage = usage.format(_enter_ks, _ks)
        try:
            if usage:
                input(prompt + _usage)
            else:
                input(prompt)
        except EOFError:
            if invert:
                return(True)
            else:
                return(False)
        return(True)

    def gpg_keygen_attribs(self):
        _strs = self.promptstr.gpg
        gpg_vals = {'attribs': {},
                    'params': {}}
        _checks = {
            'params': {
                'name': {'error': 'name cannot be empty',
                         'check': valid().nonempty_str},
                'email': {'error': 'not a valid email address',
                          'check': valid().email}
                }
            }
        for a in _strs['attribs']:
            _a = None
            while not _a:
                if 'algo' in gpg_vals['attribs'] and a == 'keysize':
                    _algo = gpg_vals['attribs']['algo']
                    _choices = _strs['attribs']['keysize']['choices'][_algo]
                    _dflt = _strs['attribs']['keysize']['default'][_algo]
                else:
                    _choices = _strs['attribs'][a]['choices']
                    _dflt = _strs['attribs'][a]['default']
                _a = (input(
                    ('\nWhat should be {0}? (Default is {1}.)\nChoices:\n'
                     '\n\t{2}\n\n{3}: ').format(
                                                _strs['attribs'][a]['text'],
                                                _dflt,
                                                '\n\t'.join(_choices),
                                                a.title()
                                                )
                                            )).strip().lower()
                if _a == '':
                    _a = _dflt
                elif _a not in _choices:
                    print(
                            ('Invalid selection; choosing default '
                             '({0})').format(_dflt)
                            )
                    _a = _dflt
            gpg_vals['attribs'][a] = _a
        for p in _strs['params']:
            _p = input(
                    ('\nWhat is the {0} for the subkey?\n'
                     '{1}: ').format(p, p.title())
                    )
            if p in _checks['params']:
                while not _checks['params'][p]['check'](_p):
                    print(
                            ('Invalid entry ({0}). Please retry.').format(
                                    _checks['params'][p]['error']
                                    )
                            )
                    _p = input('{0}: '.format(_p.title()))
            gpg_vals['params'][p] = _p
        return(gpg_vals)

    def hash_select(self, prompt = '',
                    hash_types = generate().hashlib_names()):
        _hash_types = hash_types
        _hash_str = '\n\t'.join(
            ['{0}: {1}'.format(idx, val) for idx, val in enumerate(_hash_types,
                                                                   1)
            ])
        prompt = prompt.format(_hash_str)
        _hash_select = (input(prompt)).strip()
        if not valid().integer(_hash_select):
            return(False)
        try:
            _hash_select = _hash_types[int(_hash_select) - 1]
        except IndexError:
            return(None)
        return(_hash_select)

    def multiline_input(self, prompt = None, continue_str = '> ',
                        end_str = '\n(End signal received)'):
        _lines = []
        if prompt:
            # This grabs the first CR/LF.
            _lines.append(input(prompt))
        try:
            while True:
                if continue_str:
                    _lines.append(input(continue_str))
                else:
                    _lines.append(input())
        except EOFError:
            if end_str:
                print(end_str)
        return('\n'.join(_lines))

    def path(self, path_desc, empty_passthru = False):
        path = input(('\nWhere would you like to put {0}?\n'
                      'Path: ').format(path_desc))
        if empty_passthru:
            if path.strip() == '':
                return('')
        path = transform().full_path(path)
        return(path)
    
    def ssl_object(self, pki_role, cn_url):
        ssl_vals = {'paths': {},
                    'attribs': {},
                    'subject': {}}
        _checks = {
            'subject': {
                'countryName': valid().country_abbrev,
                'emailAddress': valid().email
                }
            }
        _strs = copy.deepcopy(self.promptstr.ssl)
        # pki_role should be 'ca' or 'client'
        if pki_role not in ('ca', 'client'):
            raise ValueError('pki_role must be either "ca" or "client"')
        # NOTE: need to validate US and email
        if pki_role == 'ca':
            # this is getting triggered for clients?
            _strs['paths'].update(_strs['paths_ca'])
        for a in _strs['attribs']:
            ssl_vals['attribs'][a] = {}
            for x in _strs['attribs'][a]:
                ssl_vals['attribs'][a][x] = None
        for p in _strs['paths']:
            if p == 'csr':
                _allow_empty = True
            else:
                _allow_empty = False
            ssl_vals['paths'][p] = self.path(_strs['paths'][p],
                                             empty_passthru = _allow_empty)
            print()
            if ssl_vals['paths'][p] == '':
                ssl_vals['paths'][p] = None
            if p in _strs['attribs']:
                for x in _strs['attribs'][p]:
                    while not ssl_vals['attribs'][p][x]:
                        # cipher attrib is prompted for before this.
                        if p == 'key' and x == 'passphrase':
                            if ssl_vals['attribs']['key']['cipher'] == 'none':
                                ssl_vals['attribs'][p][x] = 'none'
                                continue
                            ssl_vals['attribs'][p][x] = getpass.getpass(
                                    ('{0}\n{1}').format(
                                            _strs['attribs'][p][x]['text'],
                                            _strs['attribs'][p][x]['prompt'])
                                    )
                            if ssl_vals['attribs'][p][x] == '':
                                ssl_vals['attribs'][p][x] = 'none'
                        else:
                            ssl_vals['attribs'][p][x] = (input(
                                ('\n{0}\n\n\t{1}\n\n{2}').format(
                                                _strs['attribs'][p][x]['text'],
                                                '\n\t'.join(
                                            _strs['attribs'][p][x]['options']),
                                            _strs['attribs'][p][x]['prompt']))
                                                ).strip().lower()
                            if ssl_vals['attribs'][p][x] not in \
                                            _strs['attribs'][p][x]['options']:
                                print(
                                        ('\nInvalid selection; setting default '
                                       '({0}).').format(
                                            _strs['attribs'][p][x]['default']
                                                )
                                        )
                                ssl_vals['attribs'][p][x] = \
                                            _strs['attribs'][p][x]['default']
        for s in _strs['subject']:
            ssl_vals['subject'][s] = None
        for s in _strs['subject']:
            while not ssl_vals['subject'][s]:
                _input = (input(
                            ('\nWhat is {0}').format(
                                _strs['subject'][s]['text'])
                        )).strip()
                print()
                if s in _checks['subject']:
                    if not _checks['subject'][s](_input):
                        print('Invalid entry; try again.')
                        ssl_vals['subject'][s] = None
                        continue
                ssl_vals['subject'][s] = _input
        _url = transform().url_to_dict(cn_url, no_None = True)
        ssl_vals['subject']['commonName'] = _url['host']
        if pki_role == 'client':
            ssl_vals['subject']['commonName'] += ' (Client)'
        return(ssl_vals)

class transform(object):
    def __init__(self):
        pass

    def flatten_recurse(self, obj, values = []):
        _values = values
        if isinstance(obj, list):
            _values += obj
        elif isinstance(obj, str):
            _values.append(obj)
        elif isinstance(obj, dict):
            for k in obj:
                self.flatten_recurse(obj[k], values = _values)
        return(_values)

    def no_newlines(self, text_in):
        text = re.sub('\n+', ' ', text_in)
        return(text)

    def full_path(self, path):
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        return(path)

    def py2xml(self, value, attrib = True):
        if value in (False, ''):
            if attrib:
                return("no")
            else:
                return(None)
        elif isinstance(value, bool):
            # We handle the False case above.
            return("yes")
        elif isinstance(value, str):
            return(value)
        else:
            # We can't do it simply.
            return(value)

    def sanitize_input(self, text_in, no_underscores = False):
        if no_underscores:
            _ws_repl = ''
        else:
            _ws_repl = '_'
        # First we convert spaces to underscores (or remove them entirely).
        text_out = re.sub('\s+', _ws_repl, text_in.strip())
        # Then just strip out all symbols.
        text_out = re.sub('[^\w]', '', text_out)
        return(text_out)

    # noinspection PyDictCreation
    def url_to_dict(self, orig_url, no_None = False):
        def _getuserinfo(uinfo_str):
            if len(uinfo_str) == 0:
                if no_None:
                    return('')
                else:
                    return(None)
            else:
                uinfo_str = uinfo_str[0]
            _l = [i.strip() for i in uinfo_str.split(':') if i.strip() != '']
            if len(_l) == 1:
                _l.append('')
            elif len(_l) == 0:
                if no_None:
                    return('')
                else:
                    return(None)
            uinfo = {}
            if not no_None:
                uinfo['user'] = (None if _l[0] == '' else _l[0])
                uinfo['password'] = (None if _l[1] == '' else _l[1])
            else:
                uinfo['user'] = _l[0]
                uinfo['password'] = _l[1]
            return(uinfo)
        def _getdfltport():
            with open('/etc/services', 'r') as f:
                _svcs = f.read()
            _svcs = [i.strip() for i in _svcs.splitlines() if i.strip() != '']
            svcs = {}
            for x in _svcs:
                if re.search('^\s*#', x):
                    continue
                s = re.sub('^\s*(\w\s+\w)(\s|\s*#)*.*$', '\g<1>', x)
                l = [i.strip() for i in s.split()]
                p = (int(l[1].split('/')[0]), l[1].split('/')[1])
                if l[0] not in svcs:
                    svcs[l[0]] = []
                if len(svcs[l[0]]) > 0:
                    # If it has a TCP port, put that first.
                    for idx, val in enumerate(svcs[l[0]]):
                        if val['proto'].lower() == 'tcp':
                            svcs[l[0]].insert(0, svcs[l[0]].pop(idx))
                svcs[l[0]].append({'port': p[0],
                                   'proto': p[1]})
            return(svcs)
        def _subsplitter(in_str, split_char):
            if in_str == '':
                if not no_None:
                    return(None)
                else:
                    return('')
            _params = {}
            for i in in_str.split(split_char):
                p = [x.strip() for x in i.split('=')]
                _params[p[0]] = p[1]
            if not _params:
                if not no_None:
                    return(None)
                else:
                    return('')
            if not _params and not no_None:
                return(None)
            return(_params)
        _dflt_ports = _getdfltport()
        scheme = None
        _scheme_re = re.compile('^([\w+.-]+)(://.*)', re.IGNORECASE)
        if not _scheme_re.search(orig_url):
            # They probably didn't prefix a URI signifier (RFC3986 § 3.1).
            # We'll add one for them.
            url = 'http://' + orig_url
            scheme = 'http'
        else:
            # urlparse's .scheme? Total trash.
            url = orig_url
            scheme = _scheme_re.sub('\g<1>', orig_url)
        url_split = urlparse(url)
        # Get any userinfo present.
        _auth = url_split.netloc.split('@')[:-1]
        userinfo = _getuserinfo(_auth)
        # Get any port specified (and parse the host at the same time).
        if userinfo:
            _h_split = url_split.netloc('@')[-1]
        else:
            _h_split = url_split.netloc
        _nl_split = _h_split.split(':')
        if len(_nl_split) > 1:
            if userinfo in (None, ''):
                port = int(_nl_split[1])
                host = _nl_split[0]
            else:
                port = int(_nl_split[-1])
                host = _nl_split[-2]
        else:
            if scheme in _dflt_ports:
                port = _dflt_ports[scheme][0]['port']
            else:
                if not no_None:
                    port = None
                else:
                    ''
            host = _nl_split[0]
        # Split out the params, queries, fragments.
        params = _subsplitter(url_split.params, ';')
        queries = _subsplitter(url_split.query, '?')
        fragments = _subsplitter(url_split.fragment, '#')
        if url_split.path == '':
            path = '/'
        else:
            path = os.path.dirname(url_split.path)
        _dest = os.path.basename(url_split.path)
        if not no_None:
            dest = (None if _dest == '' else _dest)
        else:
            dest = _dest
        url = {'scheme': scheme,
               'auth': userinfo,
               'host': host,
               'port': port,
               'path': path,
               'dest': dest,
               'params': params,
               'queries': queries,
               'fragments': fragments,
               'url': orig_url}
        url['full_url'] = '{0}://'.format(scheme)
        if userinfo not in (None, ''):
            url['full_url'] += '{user}:{password}@'.format(**userinfo)
        url['full_url'] += host
        if port not in (None, ''):
            url['full_url'] += ':{0}'.format(port)
        url['full_url'] += '/'.join((path, dest))
        # Do these need to be in a specific order?
        if params not in (None, ''):
            _p = ['{0}={1}'.format(k, v) for k, v in params.items()]
            url['full_url'] += ';{0}'.format(';'.join(_p))
        if queries not in (None, ''):
            _q = ['{0}={1}'.format(k, v) for k, v in queries.items()]
            url['full_url'] += '?{0}'.format('?'.join(_q))
        if fragments not in (None, ''):
            _f = ['{0}={1}'.format(k, v) for k, v in fragments.items()]
            url['full_url'] += '#{0}'.format('#'.join(_f))
        return(url)

    def user(self, user_elem):
        _attribs = ('hashed', 'hash_algo', 'salt')
        acct = {}
        for a in _attribs:
            acct[a] = None
        if len(user_elem):
            elem = user_elem[0]
            for a in _attribs:
                if a in elem.attrib:
                    acct[a] = self.xml2py(elem.attrib[a], attrib = True)
            if acct['hashed']:
                if not acct['hash_algo']:
                    _hash = detect().password_hash(elem.text)
                    if _hash:
                        acct['hash_algo'] = _hash
                    else:
                        raise ValueError(
                                'Invalid salted password hash: {0}'.format(
                                        elem.text)
                                )
                acct['salt_hash'] = elem.text
                acct['passphrase'] = None
            else:
                if not acct['hash_algo']:
                    acct['hash_algo'] = 'sha512'
                acct['passphrase'] = elem.text
            _saltre = re.compile('^\s*(auto|none|)\s*$', re.IGNORECASE)
            if acct['salt']:
                if _saltre.search(acct['salt']):
                    _salt = generate.salt(acct['hash_algo'])
                    acct['salt'] = _salt
            else:
                if not acct['hashed']:
                    acct['salt_hash'] = generate().hash_password(
                                        acct['passphrase'],
                                        algo = crypt_map[acct['hash_algo']])
                acct['salt'] = detect().password_hash_salt(acct['salt_hash'])
        if 'salt_hash' not in acct:
            acct['salt_hash'] = generate().hash_password(
                                        acct['passphrase'],
                                        salt = acct['salt'],
                                        algo = crypt_map[acct['hash_algo']])
        return(acct)

    def xml2py(self, value, attrib = True):
        yes = re.compile('^\s*(y(es)?|true|1)\s*$', re.IGNORECASE)
        no = re.compile('^\s*(no?|false|0)\s*$', re.IGNORECASE)
        none = re.compile('^\s*(none|)\s*$', re.IGNORECASE)
        if no.search(value):
            if attrib:
                return(False)
            else:
                return(None)
        elif yes.search(value):
            # We handle the False case above.
            return(True)
        elif value.strip() == '' or none.search(value):
            return(None)
        elif valid().integer(value):
            return(int(value))
        else:
            return(value)
        return()

class valid(object):
    def __init__(self):
        pass

    def country_abbrev(self, country_code):
        if country_code not in iso3166.countries_by_alpha2:
            return(False)
        return(True)

    def dns(self, addr):
        pass

    def connection(self, conninfo):
        # conninfo should ideally be (host, port)
        pass

    def email(self, addr):
        return(
            not isinstance(validators.email(emailparse(addr)[1]),
                      validators.utils.ValidationFailure))

    def gpgkeyID(self, key_id):
        # Condense fingerprints into normalized 40-char "full" key IDs.
        key_id = re.sub('\s+', '', key_id)
        _re_str = ('^(0x)?('
                   '[{HEX}]{{40}}|'
                   '[{HEX}]{{16}}|'
                   '[{HEX}]{{8}}'
                   ')$').format(HEX = string.hexdigits)
        _key_re = re.compile(_re_str)
        if not _key_re.search(key_id):
            return(False)
        return(True)

    def integer(self, num):
        try:
            int(num)
            return(True)
        except ValueError:
            return(False)
        return()

    def nonempty_str(self, str_in):
        if str_in.strip() == '':
            return(False)
        return(True)

    def password(self, passwd):
        # https://en.wikipedia.org/wiki/ASCII#Printable_characters
        # https://serverfault.com/a/513243/103116
        _chars = ('!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '[\]^_`abcdefghijklmnopqrstuvwxyz{|}~ ')
        for char in passwd:
            if char not in _chars:
                return(False)
        return(True)

    def password_hash(self, passwd_hash, algo = None):
        # We need to identify the algorithm if it wasn't provided.
        if not algo:
            # The following are supported on GNU/Linux.
            # "des_crypt" is glibc's crypt() (man 3 crypt).
            # https://passlib.readthedocs.io/en/stable/lib/passlib.context.html
            # Specifically, ...#passlib.context.CryptContext.identify
            _ctx = cryptctx(schemes = passlib_schemes)
            _algo = _ctx.identify(passwd_hash)
            if not _algo:
                return(False)
            else:
                algo = re.sub('_crypt$', '', _algo)
        _ctx = cryptctx(schemes = ['{0}_crypt'.format(algo)])
        if not _ctx.identify(passwd_hash):
            return(False)
        return(True)

    def salt_hash(self, salthash):
        _idents = ''.join([i.ident for i in crypt_map if i.ident])
        # noinspection PyStringFormat
        _regex = re.compile('^(\$[{0}]\$)?[./0-9A-Za-z]{{0,16}}\$?'.format(
                                                                    _idents))
        if not _regex.search(salthash):
            return(False)
        return(True)

    def plugin_name(self, name):
        if len(name) == 0:
            return(False)
        _name_re = re.compile('^[a-z][0-9a-z_]+$', re.IGNORECASE)
        if not _name_re.search(name):
            return(False)
        return(True)

    def posix_filename(self, fname):
        # Note: 2009 spec of POSIX, "3.282 Portable Filename Character Set"
        if len(fname) == 0:
            return(False)
        _char_re = re.compile('^[a-z0-9._-]+$', re.IGNORECASE)
        if not _char_re.search(fname):
            return(False)
        return(True)

    def url(self, url):
        if not re.search('^[\w+.-]+://', url):
            # They probably didn't prefix a URI signifier (RFC3986 § 3.1).
            # We'll add one for them.
            url = 'http://' + url
        if isinstance(validators.url(url), validators.utils.ValidationFailure):
            return(False)
        else:
            return(True)
        return()

    def username(self, uname):
        # https://unix.stackexchange.com/a/435120/284004
        _regex = re.compile('^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$')
        if not _regex.search(uname):
            return(False)
        return(True)

    def uuid(self, uuid_str):
        is_uuid = True
        try:
            u = uuid.UUID(uuid_str)
        except ValueError:
            return(False)
        if not uuid_str == str(u):
            return(False)
        return(is_uuid)

class xml_supplicant(object):
    def __init__(self, cfg, profile = None, max_recurse = 5):
        self.selector_ids = ('id', 'name', 'uuid')
        self.btags = {'xpath': {},
                      'regex': {},
                      'variable': {}}
        raw = self._detect_cfg(cfg)
        # This is changed in just a moment.
        self.profile = profile
        # This is retained so we can "refresh" the profile if needed.
        self.orig_profile = profile
        try:
            self.xml = lxml.etree.fromstring(raw)
        except lxml.etree.XMLSyntaxError:
            raise ValueError('The configuration provided does not seem to be '
                             'valid')
        self.get_profile(profile = profile)
        self.xml = lxml.etree.fromstring(raw)
        self.fmt = XPathFmt()
        self.max_recurse = int(self.profile.xpath(
                                        '//meta/max_recurse/text()')[0])
        # I don't have permission to credit them, but to the person who helped
        # me with this regex - thank you. You know who you are.
        # Originally this pattern was the one from:
        # https://stackoverflow.com/a/12728199/733214
        self.ptrn = re.compile(('(?<=(?<!\{)\{)(?:[^{}]+'
                                '|{{[^{}]*}})*(?=\}(?!\}))'))
        self.root = lxml.etree.ElementTree(self.xml)
        self._parse_regexes()
        self._parse_variables()
        
    def _detect_cfg(self, cfg):
        if isinstance(cfg, str):
            try:
                lxml.etree.fromstring(cfg.encode('utf-8'))
                return(cfg.encode('utf-8'))
            except lxml.etree.XMLSyntaxError:
                path = os.path.abspath(os.path.expanduser(cfg))
                try:
                    with open(path, 'rb') as f:
                        cfg = f.read()
                except FileNotFoundError:
                    raise ValueError('Could not open {0}'.format(path))
        elif isinstance(cfg, _io.TextIOWrapper):
            _cfg = cfg.read().encode('utf-8')
            cfg.close()
            cfg = _cfg
        elif isinstance(cfg,  _io.BufferedReader):
            _cfg = cfg.read()
            cfg.close()
            cfg = _cfg
        elif isinstance(cfg, lxml.etree._Element):
            return(lxml.etree.tostring(cfg))
        elif isinstance(cfg, bytes):
            return(cfg)
        else:
            raise TypeError('Could not determine the object type.')
        return(cfg)

    def _parse_regexes(self):
        for regex in self.profile.xpath('//meta/regexes/pattern'):
            _key = 'regex%{0}'.format(regex.attrib['id'])
            self.btags['regex'][_key] = regex.text
        return()

    def _parse_variables(self):
        for variable in self.profile.xpath('//meta/variables/variable'):
            self.btags['variable'][
                                'variable%{0}'.format(variable.attrib['id'])
                                    ] = variable.text
        return()

    def btags_to_dict(self, text_in):
        d = {}
        ptrn_id = self.ptrn.findall(text_in)
        if len(ptrn_id) >= 1:
            for item in ptrn_id:
                try:
                    btag, expr = item.split('%', 1)
                    if btag not in self.btags:
                        continue
                    if item not in self.btags[btag]:
                        self.btags[btag][item] = None
                    #self.btags[btag][item] = expr # remove me?
                    if btag == 'xpath':
                        d[item] = (btag, expr)
                    elif btag == 'variable':
                        d[item] = (btag, self.btags['variable'][item])
                except ValueError:
                    return(d)
        return(d)

    def get_profile(self, profile = None):
        """Get a configuration profile.

        Get a configuration profile from the XML object and set that as a
        profile object. If a profile is specified, attempt to find it. If not,
        follow the default rules as specified in __init__.
        """
        if profile:
            # A profile identifier was provided
            if isinstance(profile, str):
                _profile_name = profile
                profile = {}
                for i in self.selector_ids:
                    profile[i] = None
                profile['name'] = _profile_name
            elif isinstance(profile, dict):
                for k in self.selector_ids:
                    if k not in profile.keys():
                        profile[k] = None
            else:
                raise TypeError('profile must be a string (name of profile), '
                                'a dictionary, or None')
            xpath = '/bdisk/profile{0}'.format(self.xpath_selector(profile))
            self.profile = self.xml.xpath(xpath)
            if len(self.profile) != 1:
                raise ValueError('Could not determine a valid, unique '
                                 'profile; please check your profile '
                                 'specifier(s)')
            else:
                # We need the actual *profile*, not a list of matching
                # profile(s).
                self.profile = self.profile[0]
            if not len(self.profile):
                raise RuntimeError('Could not find the profile specified in '
                                   'the given configuration')
        else:
            # We need to find the default.
            profiles = []
            for p in self.xml.xpath('/bdisk/profile'):
                profiles.append(p)
            # Look for one named "default" or "DEFAULT" etc.
            for idx, value in enumerate([e.attrib['name'].lower() \
                                         for e in profiles]):
                if value == 'default':
                    #self.profile = copy.deepcopy(profiles[idx])
                    self.profile = profiles[idx]
                    break
            # We couldn't find a profile with a default name. Try to grab the
            # first profile.
            if self.profile is None:
                # Grab the first profile.
                if profiles:
                    self.profile = profiles[0]
                else:
                    # No profiles found.
                    raise RuntimeError('Could not find any usable '
                                       'configuration profiles')
        return()

    def get_path(self, element):
        path = element
        try:
            path = self.root.getpath(element)
        except ValueError:
            raise ValueError(
                (
                    'Could not find a path for the expression {0}'
                ).format(element.text))
        return(path)

    def substitute(self, element, recurse_count = 0):
        if recurse_count >= self.max_recurse:
            return(element)
        if isinstance(element, lxml.etree._Element):
            if element.tag == 'regex':
                return(element)
            if isinstance(element, lxml.etree._Comment):
                return(element)
            if element.text:
                _dictmap = self.btags_to_dict(element.text)
                for elem in _dictmap:
                    # This is needed because _dictmap gets replaced below
                    if not _dictmap:
                        return(element)
                    _btag, _value = _dictmap[elem]
                    if isinstance(_value, str):
                        if _btag == 'xpath':
                            try:
                                newpath = element.xpath(_dictmap[elem][1])
                            except (AttributeError, IndexError, TypeError):
                                newpath = element
                            except lxml.etree.XPathEvalError:
                                return(element)
                            try:
                                self.btags['xpath'][elem] = self.substitute(
                                            newpath, (recurse_count + 1))[0]
                            except (IndexError, TypeError):
                                raise ValueError(
                                    ('Encountered an error while trying to '
                                     'substitute {0} at {1}').format(
                                        elem, self.get_path(element)
                                    ))
                        element.text = self.fmt.vformat(
                                            element.text,   
                                            [],
                                            {**self.btags['xpath'],
                                             **self.btags['variable']})
                        _dictmap = self.btags_to_dict(element.text)
        return(element)

    def xpath_selector(self, selectors):
        # selectors is a dict of {attrib:value}
        xpath = ''
        for i in selectors.items():
            if i[1] and i[0] in self.selector_ids:
                xpath += '[@{0}="{1}"]'.format(*i)
        return(xpath)