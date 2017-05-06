import os
from io import BytesIO
import subprocess
import datetime
import jinja2
import gpgme
import psutil

def genGPG(conf):
    # https://media.readthedocs.org/pdf/pygpgme/latest/pygpgme.pdf
    build = conf['build']
    dlpath = build['dlpath']
    bdisk = conf['bdisk']
    gpghome = conf['gpg']['mygpghome']
    distkeys = []
    gpgkeyserver = []
    for a in conf['build']['arch']:
        keysrv = conf['src'][a]['gpgkeyserver']
        distkey = conf['src'][a]['gpgkey']
        if keysrv and (keysrv not in gpgkeyserver):
            gpgkeyserver.append(keysrv)
        if distkey and(distkey not in distkeys):
            distkeys.append(distkey)
    templates_dir = '{0}/extra/templates'.format(build['basedir'])
    mykey = False
    pkeys = []
    killStaleAgent(conf)
    if conf['gpg']['mygpgkey'] != '':
        mykey = conf['gpg']['mygpgkey']
        if gpghome == '':
            # Let's try the default.
            gpghome = '{0}/.gnupg'.format(os.path.expanduser("~"))
    else:
        # No key ID was specified.
        if gpghome == '':
            # We'll generate a key if we can't find one here.
            gpghome = build['dlpath'] + '/.gnupg'
    killStaleAgent(conf)
    os.environ['GNUPGHOME'] = gpghome
    gpg = gpgme.Context()
    # do we need to add a keyserver?
    if len(gpgkeyserver) != 0:
        dirmgr = '{0}/dirmngr.conf'.format(gpghome)
        for s in gpgkeyserver:
            if os.path.isfile(dirmgr):
                with open(dirmgr, 'r+') as f:
                    findme = any(s in line for line in f)
                    if not findme:
                        f.seek(0, os.SEEK_END)
                        f.write("\n# Added by {0}.\nkeyserver {1}\n".format(
                                                            bdisk['pname'],
                                                            s))
    if mykey:
        try:
            pkeys.append(gpg.get_key(mykey, True))
        except:
            exit('{0}: ERROR: You specified using {1} but we have no secret key for that ID!'.format(
                                                        datetime.datetime.now(),
                                                        mykey))
    else:
        for key in gpg.keylist(None, True):
            if key.can_sign:
                pkeys.append(key)
                break
        if len(pkeys) == 0:
            print("{0}: [GPG] Generating a GPG key...".format(datetime.datetime.now()))
            loader = jinja2.FileSystemLoader(templates_dir)
            env = jinja2.Environment(loader = loader)
            tpl = env.get_template('GPG.j2')
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            privkey = gpg.get_key(gpg.genkey(tpl_out).fpr, True)
            pkeys.append(privkey)
            # do we need to add a keyserver? this is for the freshly-generated GNUPGHOME
            if len(gpgkeyserver) != 0:
                dirmgr = '{0}/dirmngr.conf'.format(gpghome)
                for s in gpgkeyserver:
                    with open(dirmgr, 'r+') as f:
                        findme = any(s in line for line in f)
                        if not findme:
                            f.seek(0, os.SEEK_END)
                            f.write("\n# Added by {0}.\nkeyserver {1}\n".format(
                                                                bdisk['pname'],
                                                                s))
    gpg.signers = pkeys
    # Now we try to find and add the key for the base image.
    gpg.keylist_mode = gpgme.KEYLIST_MODE_EXTERN  # remote (keyserver)
    if len(distkeys) > 0: # testing
        for k in distkeys:
            key = gpg.get_key(k)
            importkey = key.subkeys[0].fpr
            gpg.keylist_mode = gpgme.KEYLIST_MODE_LOCAL # local keyring (default)
            DEVNULL = open(os.devnull, 'w')
            print('{0}: [GPG] Importing {1} and signing it for verification purposes...'.format(
                                            datetime.datetime.now(),
                                            distkey))
            cmd = ['/usr/bin/gpg',
                    '--recv-keys',
                    '--batch',
                    '--yes',
                    '0x{0}'.format(importkey)]
            subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
            sigkeys = []
            for i in gpg.get_key(importkey).subkeys:
                sigkeys.append(i.fpr)
            cmd = ['/usr/bin/gpg',
                    '--batch',
                    '--yes',
                    '--lsign-key',
                    '0x{0}'.format(importkey)]
            subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
    # We need to expose this key to the chroots, too, so we need to export it.
    with open('{0}/gpgkey.pub'.format(dlpath), 'wb') as f:
        gpg.export(pkeys[0].subkeys[0].keyid, f)
    return(gpg)

def killStaleAgent(conf):
    # Kill off any stale GPG agents running.
    # Probably not even needed, but good to have.
    chrootdir = conf['build']['chrootdir']
    gpgpath = conf['gpg']['mygpghome']
    procs = psutil.process_iter()
    plst = []
    for p in procs:
        if (p.name() in ('gpg-agent', 'dirmngr') and p.uids()[0] == os.getuid()):
            pd = psutil.Process(p.pid).as_dict()
            for d in (chrootdir, gpgpath):
                if pd['cwd'].startswith('{0}'.format(d)):
                    plst.append(p.pid)
    if len(plst) >= 1:
        for p in plst:
            psutil.Process(p).terminate()

def signIMG(path, conf):
    if conf['build']['sign']:
        # Do we want to kill off any stale gpg-agents? (So we spawn a new one)
        # Requires further testing.
        #killStaleAgent()
        gpg = conf['gpgobj']
        print('{0}: [GPG] Signing {1}...'.format(
                                        datetime.datetime.now(),
                                        path))
        # May not be necessary; further testing necessary
        #if os.getenv('GPG_AGENT_INFO'):
        #    del os.environ['GPG_AGENT_INFO']
        gpg = conf['gpgobj']
        # ASCII-armor (.asc)
        gpg.armor = True
        data_in = open(path, 'rb')
        sigbuf = BytesIO()
        sig = gpg.sign(data_in, sigbuf, gpgme.SIG_MODE_DETACH)
        _ = sigbuf.seek(0)
        _ = data_in.seek(0)
        data_in.close()
        with open('{0}.asc'.format(path), 'wb') as f:
            f.write(sigbuf.read())
        print('{0}: [GPG] Wrote {1}.asc (ASCII-armored signature).'.format(
                                    datetime.datetime.now(),
                                    path))
        # Binary signature (.sig)
        gpg.armor = False
        data_in = open(path, 'rb')
        sigbuf = BytesIO()
        sig = gpg.sign(data_in, sigbuf, gpgme.SIG_MODE_DETACH)
        _ = sigbuf.seek(0)
        _ = data_in.seek(0)
        data_in.close()
        with open('{0}.sig'.format(path), 'wb') as f:
            f.write(sigbuf.read())
        print('{0}: [GPG] Wrote {1}.sig (binary signature).'.format(
                                    datetime.datetime.now(),
                                    path))

def gpgVerify(sigfile, datafile, conf):
    gpg = conf['gpgobj']
    fullkeys = []
    print('{0}: [GPG] Verifying {1} with {2}...'.format(
                                    datetime.datetime.now(),
                                    datafile,
                                    sigfile))
    keylst = gpg.keylist()
    for k in keylst:
        fullkeys.append(k.subkeys[0].fpr)
    with open(sigfile,'rb') as s:
        with open(datafile, 'rb') as f:
            sig = gpg.verify(s, f, None)
    for x in sig:
        if x.validity <= 1:
            if not x.validity_reason:
                reason = 'we require a signature trust of 2 or higher'
            else:
                reason = x.validity_reason
            print('{0}: [GPG] Key {1} failed to verify: {2}'.format(
                                datetime.datetime.now(),
                                x.fpr,
                                reason))
    verified = False
    skeys = []
    for k in sig:
        skeys.append(k.fpr)
        if k.fpr in fullkeys:
            verified = True
            break
        else:
            pass
    if verified:
        print('{0}: [GPG] {1} verified (success).'.format(
                                datetime.datetime.now(),
                                datafile))
    else:
        print('{0}: [GPG] {1} failed verification!'.format(
                                datetime.datetime.now(),
                                datafile))
    return(verified)

def delTempKeys(conf):
    # Create a config option to delete these.
    # It's handy to keep these keys, but I'd understand if
    # people didn't want to use them.
    gpg = conf['gpgobj']
    if conf['gpg']:
        keys = []
        if conf['gpgkey'] != '':
            keys.append(gpg.get_key(conf['gpgkey']))
            if conf['mygpghome'] == '':
                keys.append(gpg.get_key(None, True))  # this is safe; we generated our own
        for k in keys:
            gpg.delete(k)
    killStaleAgent(conf)
