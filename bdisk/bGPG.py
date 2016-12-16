import os
import subprocess
import datetime
import jinja2
import gpgme
import psutil

def genGPG(conf):
    # https://media.readthedocs.org/pdf/pygpgme/latest/pygpgme.pdf
    build = conf['build']
    gpghome = conf['gpg']['mygpghome']
    distkey = build['gpgkey']
    templates_dir = '{0}/extra/templates'.format(build['basedir'])
    mykey = False
    pkeys = []
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
    os.environ['GNUPGHOME'] = gpghome
    gpg = gpgme.Context()
    if mykey:
        try:
            privkey = gpg.get_key(mykey, True)
        except:
            exit('{0}: ERROR: You specified using {1} but we have no secret key for that ID!'.format(
                                                        datetime.datetime.now(),
                                                        mykey))
    else:
        for key in gpg.keylist(None,True):
            if key.can_sign:
                pkeys.append(key)
                break
            #for subkey in key.subkeys:  # for parsing each and every subkey- this should be unnecessary
                #if subkey.can_sign:
                    #pkeys.append(gpg.get_key(subkey.fpr))
        if len(pkeys) == 0:
            print("{0}: [GPG] Generating a GPG key...".format(datetime.datetime.now()))
            loader = jinja2.FileSystemLoader(templates_dir)
            env = jinja2.Environment(loader = loader)
            tpl = env.get_template('GPG.j2')
            tpl_out = tpl.render(build = build, bdisk = bdisk)
            privkey = gpg.get_key(gpg.genkey(tpl_out).fpr, True)
            pkeys.append(privkey)
    # Now we try to find and add the key for the base image.
    gpg.keylist_mode = 2  # remote (keyserver)
    try:
        key = gpg.get_key(distkey)
    except:
        exit('{0}: ERROR: We cannot find key ID {1}!'.format(
                                    datetime.datetime.now(),
                                    distkey))
    importkey = key.subkeys[0].fpr
    gpg.keylist_mode = 1 # local keyring (default)
    DEVNULL = open(os.devnull, 'w')
    cmd = ['/usr/bin/gpg',
            '--recv-keys',
            '--batch',
            '--yes',
            '0x{0}'.format(importkey)]
    subprocess.call(cmd, stdout = DEVNULL, stderr = subprocess.STDOUT)
    sigkeys = []
    for k in gpg.get_key(importkey).subkeys:
        signkeys.append(k.fpr)


    # RETURNS:
    # our private/signing keys: privkey (is a list)
    

def killStaleAgent():
    # Kill off any stale GPG agents running.
    # Probably not even needed, but good to have.
    procs = psutil.process_iter()
    plst = []
    for p in procs:
        if (p.name() == 'gpg-agent' and p.uids()[0] == os.getuid()):
            pd = psutil.Process(p.pid).as_dict()
            if pd['cwd'] != '/':
                plst.append(p.pid)
    if len(plst) >= 1:
        for p in plst:
            psutil.Process(p).terminate()

def signIMG(path, conf):
    if conf['build']['gpg']:
        # If we enabled GPG signing, we need to figure out if we
        # are using a personal key or the automatically generated one.
        if conf['gpg']['mygpghome'] != '':
            gpghome = conf['gpg']['mygpghome']
        else:
            gpghome = conf['build']['dlpath'] + '/.gnupg'
        if conf['gpg']['mygpgkey'] != '':
            keyid = conf['gpg']['mygpgkey']
        else:
            keyid = False
        # We want to kill off any stale gpg-agents so we spawn a new one.
        killStaleAgent()
        ## HERE BE DRAGONS. Converting to PyGPGME...
        # List of Key instances used for signing with sign() and encrypt_sign().
        gpg = gpgme.Context()
        if keyid:
            gpg.signers = gpg.get_key(keyid)
        else:
            # Try to "guess" the key ID.
            # If we got here, it means we generated a key earlier during the tarball download...
            # So we can use that!
            pass
        # And if we didn't specify one manually, we'll pick the first one we find.
        # This way we can use the automatically generated one from prep.
        if not keyid:
            keyid = gpg.list_keys(True)[0]['keyid']
        print('{0}: [BUILD] Signing {1} with {2}...'.format(
                                        datetime.datetime.now(),
                                        path,
                                        keyid))
        # TODO: remove this warning when upstream python-gnupg fixes
        print('\t\t\t    If you see a "ValueError: Unknown status message: \'KEY_CONSIDERED\'" error, ' +
                'it can be safely ignored.')
        print('\t\t\t    If this is taking a VERY LONG time, try installing haveged and starting it. ' +
                'This can be done safely in parallel with the build process.')
        data_in = open(path, 'rb')
        gpg.sign_file(data_in, keyid = keyid, detach = True,
                            clearsign = False, output = '{0}.sig'.format(path))
        data_in.close()

def gpgVerify(sigfile, datafile, conf):
    pass
