import copy
import datetime
import gpg
import operator
import os
import re
import utils  # LOCAL
from functools import reduce
from gpg import gpgme

# Reference material.
# http://files.au.adversary.org/crypto/GPGMEpythonHOWTOen.html
# https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gpgme.git;a=tree;f=lang/python/examples;hb=HEAD
# https://www.gnupg.org/documentation/manuals/gpgme.pdf
# Support ECC? https://www.gnupg.org/faq/whats-new-in-2.1.html#ecc
# section 4.1, 4.2, 7.5.1, 7.5.5 in gpgme manual

# These are static values. We include them in the parent so we don't define them every time a function is called.
# Key signature attributes.
_keysig_attrs = ('comment', 'email', 'expired', 'expires', 'exportable', 'invalid', 'keyid', 'name', 'notations',
                 'pubkey_algo', 'revoked', 'sig_class', 'status', 'timestamp', 'uid')
# Data signature attributes.
_sig_attrs = ('chain_model', 'exp_timestamp', 'fpr', 'hash_algo', 'is_de_vs', 'key', 'notations', 'pka_address',
              'pka_trust', 'pubkey_algo', 'status', 'summary', 'timestamp', 'validity', 'validity_reason',
              'wrong_key_usage')

# A regex that ignores signature verification validity errors we don't care about.
_valid_ignore = re.compile(('^('
                            #'CHECKSUM|'
                            'ELEMENT_NOT_FOUND|'
                            'MISSING_VALUE|'
                            #'UNKNOWN_PACKET|'
                            'UNSUPPORTED_CMS_OBJ|'
                            'WRONG_SECKEY|'
                                '('
                                    'DECRYPT|'
                                    'INV|'
                                    'NO|'
                                    'PIN|'
                                    'SOURCE'
                                ')_'
                            ')'))
# A function to build a list based on the above.
def _gen_valid_validities():
    # Strips out and minimizes the error output.
    v = {}
    for s in dir(gpg.constants.validity):
        if _valid_ignore.search(s):
            continue
        val = getattr(gpg.constants.validity, s)
        if not isinstance(val, int):
            continue
        v[s] = val
    return(v)
_valid_validities = _gen_valid_validities()
def _get_sigstatus(status):
    statuses = []
    for e in _valid_validities:
        if ((status & _valid_validities[e]) == _valid_validities[e]):
            statuses.append(e)
    return(statuses)
def _get_sig_isgood(sigstat):
    is_good = True
    if not ((sigstat & gpg.constants.sigsum.GREEN) == gpg.constants.sigsum.GREEN):
        is_good = False
    if not ((sigstat & gpg.constants.sigsum.VALID) == gpg.constants.sigsum.VALID):
        is_good = False
    return(is_good)


# This helps translate the input name from the conf to a string compatible with the gpg module.
_algmaps = {#'cv': 'cv{keysize}',  # DISABLED, can't sign (only encrypt). Currently only 25519
            'ed': 'ed{keysize}',  # Currently only 25519
            #'elg': 'elg{}',  # DISABLED, can't sign (only encrypt). 1024, 2048, 4096
            'nist': 'nistp{keysize}',  # 256, 384, 521
            'brainpool.1': 'brainpoolP{keysize}r1',  # 256, 384, 512
            'sec.k1': 'secp{keysize}k1',  # Currently only 256
            'rsa': 'rsa{keysize}',  # Variable (1024 <> 4096), but we only support 1024, 2048, 4096
            'dsa': 'dsa{keysize}'}  # Variable (768 <> 3072), but we only support 768, 2048, 3072

# This is just a helper function to get a delta from a unix epoch.
def _epoch_helper(epoch):
    d = datetime.datetime.utcfromtimestamp(epoch) - datetime.datetime.utcnow()
    return(abs(int(d.total_seconds())))  # Returns a positive integer even if negative...
    #return(int(d.total_seconds()))

# _KeyEditor and _getEditPrompt are used to interactively edit keys -- notably currently used for editing trusts
# (since there's no way to edit trust otherwise).
# https://www.gnupg.org/documentation/manuals/gpgme/Advanced-Key-Editing.html
# https://www.apt-browse.org/browse/debian/wheezy/main/amd64/python-pyme/1:0.8.1-2/file/usr/share/doc/python-pyme/examples/t-edit.py
# https://searchcode.com/codesearch/view/20535820/
# https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob;f=doc/DETAILS
# You can get the prompt identifiers and status indicators without grokking the source
# by first interactively performing the type of edit(s) you want to do with this command:
# gpg --expert --status-fd 2 --command-fd 2 --edit-key <KEY_ID>
# Per:
# https://lists.gnupg.org/pipermail/gnupg-users/2002-April/012630.html
# https://lists.gt.net/gnupg/users/9544
# https://raymii.org/s/articles/GPG_noninteractive_batch_sign_trust_and_send_gnupg_keys.html
class _KeyEditor(object):
    def __init__(self, optmap):
        self.replied_once = False  # This is used to handle the first prompt vs. the last
        self.optmap = optmap

    def editKey(self, status, args, out):
        result = None
        out.seek(0, 0)
        def mapDict(m, d):
            return(reduce(operator.getitem, m, d))
        if args == 'keyedit.prompt' and self.replied_once:
            result = 'quit'
        elif status == 'KEY_CONSIDERED':
            result = None
            self.replied_once = False
        elif status == 'GET_LINE':
            self.replied_once = True
            _ilist = args.split('.')
            result = mapDict(_ilist, self.optmap['prompts'])
            if not result:
                result = None
        return(result)

def _getEditPrompt(key, trust, cmd, uid = None):
    if not uid:
        uid = key.uids[0]
    # This mapping defines the default "answers" to the gpgme key editing.
    # https://www.apt-browse.org/browse/debian/wheezy/main/amd64/python-pyme/1:0.8.1-2/file/usr/share/doc/python-pyme/examples/t-edit.py
    # https://searchcode.com/codesearch/view/20535820/
    # https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob;f=doc/DETAILS
    # You can get the prompt identifiers and status indicators without grokking the source
    # by first interactively performing the type of edit(s) you want to do with this command:
    # gpg --status-fd 2 --command-fd 2 --edit-key <KEY_ID>
    if trust >= gpg.constants.validity.FULL:  # For tsigning, it only prompts for two trust levels:
        _loctrust = 2  # "I trust fully"
    else:
        _loctrust = 1  # "I trust marginally"
    # TODO: make the trust depth configurable. 1 is probably the safest, but we try to guess here.
    # "Full" trust is a pretty big thing.
    if trust >= gpg.constants.validity.FULL:
        _locdepth = 2  # Allow +1 level of trust extension
    else:
        _locdepth = 1  # Only trust this key
    # The check level.
    # (0) I will not answer. (default)
    # (1) I have not checked at all.
    # (2) I have done casual checking.
    # (3) I have done very careful checking.
    # Since we're running this entirely non-interactively, we really should use 1.
    _chk_lvl = 1
    _map = {
        # Valid commands
        'cmds': ['trust', 'fpr', 'sign', 'tsign', 'lsign', 'nrsign', 'grip', 'list',
                 'uid', 'key', 'check', 'deluid', 'delkey', 'delsig', 'pref', 'showpref',
                 'revsig', 'enable', 'disable', 'showphoto', 'clean', 'minimize', 'save',
                 'quit'],
        # Prompts served by the interactive session, and a map of their responses.
        # It's expanded in the parent call, but the prompt is actually in the form of e.g.:
        # keyedit.save (we expand that to a list and use that list as a "path" in the below dict)
        # We *could* just use a flat dict of full prompt to constants, but this is a better visual segregation &
        # prevents unnecessary duplication.
        'prompts': {
            'edit_ownertrust': {'value': str(trust),  # Pulled at time of call
                                'set_ultimate': {'okay': 'yes'}},  # If confirming ultimate trust, we auto-answer yes
            'untrusted_key': {'override': 'yes'},  # We don't care if it's untrusted
            'pklist': {'user_id': {'enter': uid.uid}},  # Prompt for a user ID - can we use the full uid string? (tsign)
            'sign_uid': {'class': str(_chk_lvl),  # The certification/"check" level
                         'okay': 'yes'},  # Are you sure that you want to sign this key with your key..."
            'trustsig_prompt': {'trust_value': str(_loctrust),  # This requires some processing; see above
                                'trust_depth': str(_locdepth),  # The "depth" of the trust signature.
                                'trust_regexp': None},  # We can "Restrict" trust to certain domains if we wanted.
            'keyedit': {'prompt': cmd,  # Initiate trust editing (or whatever)
                        'save': {'okay': 'yes'}}}}  # Save if prompted
    return(_map)



class GPGHandler(object):
    def __init__(self, gnupg_homedir = None, key_id = None, keyservers = None):
        self.home = gnupg_homedir
        self.key_id = key_id
        self.keyservers = keyservers
        if self.home:
            self._prep_home()
        else:
            self._check_home()
        self.ctx = self.GetContext(home_dir = self.home)
        self._orig_kl_mode = self.ctx.get_keylist_mode()
        self.mykey = None
        self.subkey = None
        if self.key_id:
            self.mykey = self.ctx.get_key(self.key_id, secret = True)
            for s in self.mykey.subkeys:
                if s.can_sign:
                    self.subkey = s
                    self.ctx.signers = [self.mykey]
                    break

    def _check_home(self, home = None):
        if not home:
            home = self.home
        if not home:
            self.home = os.environ.get('GNUPGHOME', '~/.gnupg')
            home = self.home
        self._prep_home(home)
        return()

    def _prep_home(self, home = None):
        if not home:
            home = self.home
        if not home:
            self.home = os.environ.get('GNUPGHOME', '~/.gnupg')
        self.home = os.path.abspath(os.path.expanduser(self.home))
        if os.path.isdir(self.home):
            _exists = True
        else:
            _exists = False
        _uid = os.getuid()
        _gid = os.getgid()
        try:
            os.makedirs(self.home, exist_ok = True)
            os.chown(self.home, _uid, _gid)
            os.chmod(self.home, 0o700)
        except PermissionError:
            # It's alright; it's HOPEFULLY already created.
            if not _exists:
                raise PermissionError('We need a GnuPG home directory we can '
                                      'write to')
        # TODO: write gpg.conf, parse existing one and write changes if needed.
        # Should use SHA512 etc. See:
        # https://spin.atomicobject.com/2013/11/24/secure-gpg-keys-guide/
        # https://github.com/BetterCrypto/Applied-Crypto-Hardening/blob/master/src/configuration/GPG/GnuPG/gpg.conf
        # https://riseup.net/en/security/message-security/openpgp/best-practices
        # And explicitly set keyservers if present in params.
        return()

    def GetContext(self, **kwargs):
        ctx = gpg.Context(**kwargs)
        return(ctx)

    def CreateKey(self, name, algo, keysize, email = None, comment = None, passwd = None, key = None, expiry = None):
        userid = name
        userid += ' ({0})'.format(comment) if comment else ''
        userid += ' <{0}>'.format(email) if email else ''
        if not expiry:
            expires = False
        else:
            expires = True
        params = {'algorithm': _algmaps[algo].format(keysize = keysize),
                  'expires': expires,
                  'expires_in': (_epoch_helper(expiry) if expires else 0),
                  'sign': True,
                  'passphrase': passwd}
        if not key:
            self.mykey = self.ctx.get_key(self.ctx.create_key(userid, **params).fpr)
            self.subkey = self.mykey.subkeys[0]
        else:
            if not self.mykey:
                self.mykey = self.ctx.get_key(self.ctx.create_key(userid, **params).fpr)
            self.subkey = self.ctx.get_key(self.ctx.create_subkey(self.mykey, **params).fpr)
        self.ctx.signers = [self.subkey]
        return()

    def ListSigs(self, sig_data):
        key_ids = []
        # Currently as of May 13, 2018 there's no way using the GPGME API to do
        # the equivalent of the CLI's --list-packets. https://dev.gnupg.org/T3734
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/059708.html
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/059715.html
        # We use the "workaround" in:
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/059711.html
        try:
            self.ctx.verify(sig_data)
        except gpg.errors.BadSignatures as sig_except:
            for line in [i.strip() for i in str(sig_except).splitlines()]:
                l = [i.strip() for i in line.split(':')]
                key_ids.append(l[0])
        return(key_ids)

    def GetSigs(self, data_in, sig_data = None, verify_keys = None):
        signers = []
        if verify_keys:
            # Raises gpg.errors.BadSignatures if any are invalid.
            # Unlike Verify below, this will raise an exception.
            signers = verify_keys
        if sig_data:
            # Detached sig
            sig = self.ctx.verify(data_in, signature = sig_data, verify = signers)
        else:
            # Cleartext? or "normal" signatures (embedded)
            sig = self.ctx.verify(data_in, verify = signers)
        return(sig)

    def GetKeysigs(self, pubkey):
        sigs = {}
        fpr = (pubkey if isinstance(pubkey, str) else pubkey.fpr)
        keys = list(self.ctx.keylist(fpr, mode = (gpg.constants.keylist.mode.LOCAL | gpg.constants.keylist.mode.SIGS)))
        for idx1, k in enumerate(keys):
            sigs[k.fpr] = {}
            for idx2, u in enumerate(k.uids):
                sigs[k.fpr][u.uid] = {}
                for idx3, sig in enumerate(u.signatures):
                    signer = getattr(sig, 'keyid')
                    sigs[k.fpr][u.uid][signer] = {}
                    for a in _keysig_attrs:
                        if a == 'keyid':
                            continue
                        sigs[k.fpr][u.uid][signer][a] = getattr(sig, a)
        return(sigs)

    def CheckSigs(self, sig, sigkeys = None):
        # sig should be a GetSigs result.
        is_valid = True
        # See self.CheckSigs().
        # https://www.gnupg.org/documentation/manuals/gpgme/Verify.html
        # https://github.com/micahflee/torbrowser-launcher/issues/262#issuecomment-284342876
        sig = sig[1]
        result = {}
        _keys = [s.fpr.upper() for s in sig.signatures]
        if sigkeys:
            if isinstance(sigkeys, str):
                sigkeys = [sigkeys.upper()]
            elif isinstance(sigkeys, list):
                _sigkeys = []
                for s in sigkeys[:]:
                    if isinstance(s, str):
                        _sigkeys.append(s.upper())
                    elif isinstance(s, gpgme._gpgme_key):
                        _sigkeys.append(s.fpr)
                    else:
                        continue
                sigkeys = _sigkeys
            elif isinstance(sigkeys, gpgme._gpgme_key):
                sigkeys = [sigkeys.fpr]
            else:
                raise ValueError('sigkeys must be a key fingerprint or a key object (or a list of those).')
            if not set(sigkeys).issubset(_keys):
                raise ValueError('All specified keys were not present in the signature.')
        for s in sig.signatures:
            fpr = getattr(s, 'fpr')
            result[fpr] = {}
            for a in _sig_attrs:
                if a == 'fpr':
                    continue
                result[fpr][a] = getattr(s, a)
            # Now we do some logic to determine if the sig is "valid".
            # Note that we can get confidence level by &'ing "validity" attr against gpg.constants.validity.*
            # Or just doing a <, >, <=, etc. operation since it's a sequential list of constants levels, not bitwise.
            # For now, we just check if it's valid or not, not "how valid" it is (how much we can trust it).
            _status = s.summary
            if not _get_sig_isgood(_status):
                result[fpr]['valid'] = False
            else:
                result[fpr]['valid'] = True
        if sigkeys:
            for k in sigkeys:
                if (k not in result) or (not result[k]['valid']):
                    is_valid = False
                    break
        else:  # is_valid is satisfied by at LEAST one valid sig.
            is_valid = any([k[1]['valid'] for k in result])
        return(is_valid, result)

    def Sign(self, data_in, ascii = True, mode = 'detached', notations = None):
        # notations is a list of dicts via notation format:
        # {<namespace>: {'value': 'some string', 'flags': BITWISE_OR_FLAGS}}
        # See RFC 4880 § 5.2.3.16 for valid user namespace format.
        if mode.startswith('d'):
            mode = gpg.constants.SIG_MODE_DETACH
        elif mode.startswith('c'):
            mode = gpg.constants.SIG_MODE_CLEAR
        elif mode.startswith('n'):
            mode = gpg.constants.SIG_MODE_NORMAL
        self.ctx.armor = ascii
        if not isinstance(data_in, bytes):
            if isinstance(data_in, str):
                data_in = data_in.encode('utf-8')
            else:
                # We COULD try serializing to JSON here, or converting to a pickle object,
                # or testing for other classes, etc. But we don't.
                # TODO?
                data_in = repr(data_in).encode('utf-8')
        data_in = gpg.Data(data_in)
        if notations:
            for n in notations:
                if not utils.valid().gpgsigNotation(n):
                    raise ValueError('Malformatted notation: {0}'.format(n))
                for ns in n:
                    self.ctx.sig_notation_add(ns, n[ns]['value'], n[ns]['flags'])
        # data_in *always* must be a bytes (or bytes-like?) object.
        # It will *always* return a bytes object.
        sig = self.ctx.sign(data_in, mode = mode)
        # And we need to clear the sig notations, otherwise they'll apply to the next signature this context makes.
        self.ctx.sig_notation_clear()
        return(sig)

    def ImportPubkey(self, pubkey):
        fpr = (pubkey if isinstance(pubkey, str) else pubkey.fpr)
        try:
            self.ctx.get_key(fpr)
            return()  # already imported
        except gpg.errors.KeyNotFound:
            pass
        _dflt_klm = self.ctx.get_keylist_mode()
        self.ctx.set_keylist_mode(gpg.constants.keylist.mode.EXTERN)
        if isinstance(pubkey, gpgme._gpgme_key):
            self.ctx.op_import_keys([pubkey])
        elif isinstance(pubkey, str):
            if not utils.valid().gpgkeyID(pubkey):
                raise ValueError('{0} is not a valid key or fingerprint'.format(pubkey))
            pubkey = self.ctx.get_key(fpr)
            self.ctx.op_import_keys([pubkey])
        self.ctx.set_keylist_mode(_dflt_klm)
        self.SignKey(pubkey)
        return()

    def ImportPubkeyFromFile(self, pubkey_data):
        _fpath = os.path.abspath(os.path.expanduser(pubkey_data))
        if os.path.isfile(_fpath):
            with open(_fpath, 'rb') as f:
                k = self.ctx.key_import(f.read())
        else:
            k = self.ctx.key_import(pubkey_data)
        pubkey = self.ctx.get_key(k)
        self.SignKey(pubkey)
        return()

    def SignKey(self, pubkey, local = False, notations = None):
        # notations is a list of dicts via notation format:
        # {<namespace>: {'value': 'some string', 'flags': BITWISE_OR_FLAGS}}
        # See RFC 4880 § 5.2.3.16 for valid user namespace format.
        if isinstance(pubkey, gpgme._gpgme_key):
            pass
        elif isinstance(pubkey, str):
            if not utils.valid().gpgkeyID(pubkey):
                raise ValueError('{0} is not a valid fingerprint'.format(pubkey))
            else:
                pubkey = self.ctx.get_key(pubkey)
        if notations:
            for n in notations:
                if not utils.valid().gpgsigNotation(n):
                    raise ValueError('Malformatted notation: {0}'.format(n))
                for ns in n:
                    self.ctx.sig_notation_add(ns, n[ns]['value'], n[ns]['flags'])
        self.ctx.key_sign(pubkey, local = local)
        self.TrustKey(pubkey)
        # And we need to clear the sig notations, otherwise they'll apply to the next signature this context makes.
        self.ctx.sig_notation_clear()
        return()

    def TrustKey(self, pubkey, trust = gpg.constants.validity.FULL):
        # We use full as the default because signatures aren't considered valid otherwise.
        # TODO: we need a way of maybe reverting/rolling back any changes we do?
        output = gpg.Data()
        _map = _getEditPrompt(pubkey, trust, 'trust')
        self.ctx.interact(pubkey, _KeyEditor(_map).editKey, sink = output, fnc_value = output)
        output.seek(0, 0)
        return()

    def ExportPubkey(self, fpr, ascii = True, sigs = False):
        orig_armor = self.ctx.armor
        self.ctx.armor = ascii
        if sigs:
            export_mode = 0
        else:
            export_mode = gpg.constants.EXPORT_MODE_MINIMAL  # default is 0; minimal strips signatures
        kb = gpg.Data()
        self.ctx.op_export_keys([self.ctx.get_key(fpr)], export_mode, kb)
        kb.seek(0, 0)
        self.ctx.armor = orig_armor
        return(kb.read())

    def DeleteKey(self, pubkey):
        if isinstance(pubkey, gpgme._gpgme_key):
            pass
        elif isinstance(pubkey, str):
            if not utils.valid().gpgkeyID(pubkey):
                raise ValueError('{0} is not a valid fingerprint'.format(pubkey))
            else:
                pubkey = self.ctx.get_key(pubkey)
        self.ctx.op_delete(pubkey, False)
        return()

    def Verify(self, sig_data, data):
        # This is a more "flat" version of CheckSigs.
        # First we need to parse the sig(s) and import the key(s) to our keyring.
        signers = self.ListSigs(sig_data)
        for signer in signers:
            self.ImportPubkey(signer)
        try:
            self.ctx.verify(data, signature = sig_data, verify = signers)
            return(True)
        except gpg.errors.BadSignatures as err:
            return(False)
