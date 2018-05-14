import crypt
import GPG
import hashid
import hashlib
import os
import re
import string
import textwrap
import uuid
import validators
import zlib
import lxml.etree
from collections import OrderedDict
from dns import resolver
from email.utils import parseaddr as emailparse
from passlib.context import CryptContext as cryptctx
from urllib.parse import urlparse

# Supported by all versions of GNU/Linux shadow
passlib_schemes = ['des_crypt', 'md5_crypt', 'sha256_crypt', 'sha512_crypt']

# Build various hash digest name lists
digest_schemes = list(hashlib.algorithms_available)
# Provided by zlib
digest_schemes.append('adler32')
digest_schemes.append('crc32')
#clean_digest_schemes = sorted(list(set(digest_schemes)))

crypt_map = {'sha512': crypt.METHOD_SHA512,
             'sha256': crypt.METHOD_SHA256,
             'md5': crypt.METHOD_MD5,
             'des': crypt.METHOD_CRYPT}

class detect(object):
    def __init__(self):
        pass

    def any_hash(self, hash_str):
        h = hashid.HashID()
        hashes = []
        for i in h.IdentifyHash(hash_str):
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

    def gpgkeyID_from_url(self, url):
        with urlparse(url) as u:
            data = u.read()
        g = GPG.GPGHandler()
        key_ids = g.get_sigs(data)
        del(g)
        return(key_ids)

    def gpgkey_info(self, keyID, secret = False):
        def _get_key():
            key = None
            try:
                key = g.get_key(keyID, secret = secret)
            except GPG.gpg.errors.KeyNotFound:
                return(None)
            except Exception:
                return(False)
            return(key)
        uids = {}
        g = GPG.GPGHandler()
        _orig_kl_mode = g.get_keylist_mode()
        if _orig_kl_mode != GPG.gpg.constants.KEYLIST_MODE_EXTERN:
            _key = _get_key()
            if not _key:
                g.set_keylist_mode(GPG.gpg.constants.KEYLIST_MODE_EXTERN)
                _key = _get_key()
        else:
            _key = _get_key()
        if not _key:
            g.set_keylist_mode(_orig_kl_mode)
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
        g.set_keylist_mode(_orig_kl_mode)
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
        return(crypt.crypt(password, _salt))

    def hashlib_names(self):
        hashes = []
        for h in sorted(digest_schemes):
            r = re.compile('^{0}$'.format(h), re.IGNORECASE)
            if len([i for i in filter(r.search, hashes)]) == 0:
                hashes.append(h)
        return(hashes)

    def salt(self, algo = 'sha512'):
        algo = crypt_map[algo]
        return(crypt.mksalt(algo))

class prompts(object):
    def __init__(self):
        pass

    def confirm_or_no(self, prompt = '', invert = False,
                      usage = '{0} to confirm, otherwise {1}...\n'):
        # A simplified version of multiline_input, really.
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
            params = {}
            for i in in_str.split(split_char):
                p = [x.strip() for x in i.split('=')]
                params[p[0]] = p[1]
            if not params:
                if not no_None:
                    return(None)
                else:
                    return('')
            if not params and not no_None:
                return(None)
            return(params)
        _dflt_ports = _getdfltport()
        scheme = None
        _scheme_re = re.compile('^([\w+\.-]+)(://.*)', re.IGNORECASE)
        if not _scheme_re.search(orig_url):
            # They probably didn't prefix a URI signifier (RFC3986 § 3.1).
            # We'll add one for them.
            url = 'http://' + url
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
        url['full_url'] = '{scheme}://'
        if userinfo not in (None, ''):
            url['full_url'] += '{user}:{password}@'.format(userinfo)
        url['full_url'] += host
        if port not in (None, ''):
            url['full_url'] += ':{0}'.format(port)
        url['full_url'] += path + dest
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

class valid(object):
    def __init__(self):
        pass

    def dns(self, addr):
        pass

    def connection(self, conninfo):
        # conninfo should ideally be (host, port)
        pass

    def email(self, addr):
        if isinstance(validators.email(emailparse(addr)[1]),
                      validators.utils.ValidationFailure):
            return(False)
        else:
            return(True)
        return()

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
        _regex = re.compile('^(\$[{0}]\$)?[./0-9A-Za-z]{0,16}\$?'.format(
                                                                    _idents))
        if not regex.search(salthash):
            return(False)
        return(True)

    def posix_filename(self, fname):
        # Note: 2009 spec of POSIX, "3.282 Portable Filename Character Set"
        if len(fname) == 0:
            return(False)
        _chars = (string.ascii_letters + string.digits + '.-_')
        for char in fname:
            if char not in _chars:
                return(False)
        return(True)

    def url(self, url):
        if not re.search('^[\w+\.-]+://', url):
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
            u = uuid.UUID(uuid_in)
        except ValueError:
            return(False)
        if not uuid_in == str(u):
            return(False)
        return(is_uuid)
