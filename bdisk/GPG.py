import datetime
import gpg
import os
import psutil
import gpg.errors


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

# http://files.au.adversary.org/crypto/GPGMEpythonHOWTOen.html
# https://www.gnupg.org/documentation/manuals/gpgme.pdf
# Support ECC? https://www.gnupg.org/faq/whats-new-in-2.1.html#ecc
# section 4.1, 4.2, 7.5.1, 7.5.5 in gpgme manual
# Please select what kind of key you want:
#    (1) RSA and RSA (default) - 1024-4096 bits
#    (2) DSA and Elgamal - 768-3072
#    (3) DSA (sign only) - 768-3072
#    (4) RSA (sign only) - 1024-4096
#    (7) DSA (set your own capabilities) - 768-3072
#    (8) RSA (set your own capabilities) - 1024-4096
#    (9) ECC and ECC - (see below)
#   (10) ECC (sign only) - (see below)
#   (11) ECC (set your own capabilities) - (see below)
# Your selection? 9
# Please select which elliptic curve you want:
#    (2) NIST P-256
#    (3) NIST P-384
#    (4) NIST P-521
#    (5) Brainpool P-256
#    (6) Brainpool P-384
#    (7) Brainpool P-512
# Your selection? 10
# Please select which elliptic curve you want:
#    (1) Curve 25519
#    (3) NIST P-256
#    (4) NIST P-384
#    (5) NIST P-521
#    (6) Brainpool P-256
#    (7) Brainpool P-384
#    (8) Brainpool P-512
#    (9) secp256k1
# gpgme key creation:
#g = gpg.Context()
#mainkey = g.create_key('test key via python <test2@test.com>', algorithm = 'rsa4096', expires = False,
#                        #certify = True,
#                        certify = False,
#                        sign = False,
#                        authenticate = False,
#                        encrypt = False)
#key = g.get_key(mainkey.fpr, secret = True)
#subkey = g.create_subkey(key, algorithm = 'rsa4096', expires = False,
#                         sign = True,
#                         #certify = False,
#                         encrypt = False,
#                         authenticate = False)


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
        return()

    def GetContext(self, **kwargs):
        ctx = gpg.Context(**kwargs)
        return(ctx)

    def KillStaleAgent(self):
        # Is this even necessary since I switched to the native gpg module instead of the gpgme one?
        _process_list = []
        # TODO: optimize; can I search by proc name?
        for p in psutil.process_iter():
            if (p.name() in ('gpg-agent', 'dirmngr') and \
                                                p.uids()[0] == os.getuid()):
                pd = psutil.Process(p.pid).as_dict()
                # TODO: convert these over
#                for d in (chrootdir, dlpath):
#                    if pd['cwd'].startswith('{0}'.format(d)):
#                        plst.append(p.pid)
#        if len(plst) >= 1:
#            for p in plst:
#                psutil.Process(p).terminate()

    def CreateKey(self, name, algo, keysize, email = None, comment = None, passwd = None, key = None, expiry = None):
        algo = _algmaps[algo].format(keysize = keysize)
        userid = name
        userid += ' ({0})'.format(comment) if comment else ''
        userid += ' <{0}>'.format(email) if email else ''
        if not expiry:
            expires = False
        else:
            expires = True
        self.ctx.create_key(userid,
                            algorithm = algo,
                            expires = expires,
                            expires_in = _epoch_helper(expiry),
                            sign = True)
        # Even if expires is False, it still parses the expiry...
        # except OverflowError:  # Only trips if expires is True and a negative expires occurred.
        #     raise ValueError(('Expiration epoch must be 0 (to disable) or a future time! '
        #                       'The specified epoch ({0}, {1}) is in the past '
        #                       '(current time is {2}, {3}).').format(expiry,
        #                                                             str(datetime.datetime.utcfromtimestamp(expiry)),
        #                                                             datetime.datetime.utcnow().timestamp(),
        #                                                             str(datetime.datetime.utcnow())))
        return(k)
        # We can't use self.ctx.create_key; it's a little limiting.
        # It's a fairly thin wrapper to .op_createkey() (the C GPGME API gpgme_op_createkey) anyways.
        flags = (gpg.constants.create.SIGN |
                 gpg.constants.create.CERT)
        if not expiry:
            flags = (flags | gpg.constants.create.NOEXPIRE)
        if not passwd:
            flags = (flags | gpg.constants.create.NOPASSWD)
        else:
            # Thanks, gpg/core.py#Context.create_key()!
            sys_pinentry = gpg.constants.PINENTRY_MODE_DEFAULT
            old_pass_cb = getattr(self, '_passphrase_cb', None)
            self.ctx.pinentry_mode = gpg.constants.PINENTRY_MODE_LOOPBACK
            def passphrase_cb(hint, desc, prev_bad, hook = None):
                return(passwd)
            self.ctx.set_passphrase_cb(passphrase_cb)
        try:
            if not key:
                try:
                    self.ctx.op_createkey(userid, algo, 0, 0, flags)
                    k = self.ctx.get_key(self.ctx.op_genkey_result().fpr, secret = True)
            else:
                if not isinstance(key, gpg.gpgme._gpgme_key):
                    key = self.ctx.get_key(key)
                if not key:
                    raise ValueError('Key {0} does not exist'.format())
                #self.ctx.op_createsubkey(key, )
        finally:
            if not passwd:
                self.ctx.pinentry_mode = sys_pinentry
                if old_pass_cb:
                    self.ctx.set_passphrase_cb(*old_pass_cb[1:])
        return(k)

    def GetSigs(self, data_in):
        key_ids = []
        # Currently as of May 13, 2018 there's no way using the GPGME API to do
        # the equivalent of the CLI's --list-packets.
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/
        #                                                           059708.html
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/
        #                                                           059715.html
        # We use the "workaround in:
        # https://lists.gnupg.org/pipermail/gnupg-users/2018-January/
        #                                                           059711.html
        try:
            self.ctx.verify(data_in)
        except gpg.errors.BadSignatures as sig_except:
            for line in [i.strip() for i in str(sig_except).splitlines()]:
                l = [i.strip() for i in line.split(':')]
                key_ids.append(l[0])
        return(key_ids)

    def CheckSigs(self, keys, sig_data):
        try:
            self.ctx.verify(sig_data)
        except:
            pass  # TODO
