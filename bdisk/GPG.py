import gpg
import os
import psutil
import gpg.errors

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
        self.ctx = self.get_context(home_dir = self.home)

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

    def get_context(self, **kwargs):
        ctx = gpg.Context(**kwargs)
        return(ctx)

    def kill_stale_agent(self):
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

    def get_sigs(self, data_in):
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
