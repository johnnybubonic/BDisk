import OpenSSL
import os
import shutil
import datetime
import re

def verifyCert(cert, key, CA = None):
    # Verify a given certificate against a certificate.
    # Optionally verify against a CA certificate as well (Hopefully. If/when PyOpenSSL ever supports it.)
    chk = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    chk.use_privatekey(key)
    chk.use_certificate(cert)
    try:
        chk.check_privatekey()
    except OpenSSL.SSL.Error:
        return(False)
        exit(("{0}: {1} does not match {2}!".format(datetime.datetime.now(), key, cert)))
    else:
        print("{0}: [SSL] Verified {1} against {2} successfully.".format(datetime.datetime.now(), key, cert))
        return(True)
    # This is disabled because there doesn't seem to currently be any way
    # to actually verify certificates against a given CA.
    #if CA:
    #    try:
    #        magic stuff here

def sslCAKey(conf):
    # TODO: use path from conf, even if it doesn't exist?
    # if it does, read it into a pkey object
    keyfile = conf['ipxe']['ssl_cakey']
    if os.path.isfile(keyfile):
        try:
            key = OpenSSL.crypto.load_privatekey(
                                        OpenSSL.crypto.FILETYPE_PEM,
                                        open(keyfile).read())
        except:
            exit('{0}: ERROR: It seems that {1} is not a proper PEM-encoded SSL key.'.format(
                                                            datetime.datetime.now(),
                                                            keyfile))
    else:
        key = OpenSSL.crypto.PKey()
        print("{0}: [SSL] Generating SSL CA key...".format(datetime.datetime.now()))
        key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
        with open(keyfile, 'wb') as f:
            f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
    return(key)

def sslCA(conf, key = None):
    # NOTE: 'key' is a pkey OBJECT, not a file.
    keyfile = conf['ipxe']['ssl_cakey']
    crtfile = conf['ipxe']['ssl_ca']
    if not key:
        if os.path.isfile(keyfile):
            try:
                key = OpenSSL.crypto.load_privatekey(
                                        OpenSSL.crypto.FILETYPE_PEM,
                                        open(keyfile).read())
            except:
                exit('{0}: ERROR: It seems that {1} is not a proper PEM-encoded SSL key.'.format(
                                                                datetime.datetime.now(),
                                                                keyfile))
        else:
            exit('{0}: ERROR: We need a key to generate a CA certificate!'.format(
                                                                datetime.datetime.now()))
    if os.path.isfile(crtfile):
        try:
            ca = OpenSSL.crypto.load_certificate(
                                        OpenSSL.crypto.FILETYPE_PEM,
                                        open(crtfile).read())
        except:
            exit('{0}: ERROR: It seems that {1} is not a proper PEM-encoded SSL certificate.'.format(
                                                                datetime.datetime.now(),
                                                                crtfile))
    else:
        domain = (re.sub('^(https?|ftp)://([a-z0-9.-]+)/?.*$', '\g<2>',
                            conf['ipxe']['uri'],
                            flags=re.IGNORECASE)).lower()
        # http://www.pyopenssl.org/en/stable/api/crypto.html#pkey-objects
        # http://docs.ganeti.org/ganeti/2.14/html/design-x509-ca.html
        ca = OpenSSL.crypto.X509()
        ca.set_version(3)
        ca.set_serial_number(1)
        #ca.get_subject().CN = domain
        ca.get_subject().CN = '{0} CA'.format(conf['bdisk']['name'])
        ca.gmtime_adj_notBefore(0)
        # valid for ROUGHLY 10 years. years(ish) * days * hours * mins * secs.
        # the paramater is in seconds, which is why we need to multiply them all together.
        ca.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  
        ca.set_issuer(ca.get_subject())
        ca.set_pubkey(key)
        ca.add_extensions([
                OpenSSL.crypto.X509Extension(b"basicConstraints",
                                            True,
    		    	                b"CA:TRUE, pathlen:0"),
                OpenSSL.crypto.X509Extension(b"keyUsage",
                                            True,
                                            b"keyCertSign, cRLSign"),
                OpenSSL.crypto.X509Extension(b"subjectKeyIdentifier",
                                            False,
                                            b"hash",
                                            subject = ca),])
        ca.sign(key, "sha512")
        with open(crtfile, 'wb') as f:
            f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
    return(ca)

def sslCKey(conf):
    keyfile = conf['ipxe']['ssl_key']
    if os.path.isfile(keyfile):
        try:
            key = OpenSSL.crypto.load_privatekey(
                                        OpenSSL.crypto.FILETYPE_PEM,
                                        open(keyfile).read())
        except:
            exit('{0}: ERROR: It seems that {1} is not a proper PEM-encoded SSL key.'.format(
                                                    datetime.datetime.now(),
                                                    keyfile))
    else:
        key = OpenSSL.crypto.PKey()
        print("{0}: [SSL] Generating SSL Client key...".format(datetime.datetime.now()))
        key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
        with open(keyfile, 'wb') as f:
            f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
    return(key)

def sslCSR(conf, key = None):
    # NOTE: 'key' is a pkey OBJECT, not a file.
    keyfile = conf['ipxe']['ssl_key']
    crtfile = conf['ipxe']['ssl_crt']
    if not key:
        if os.path.isfile(keyfile):
            try:
                key = OpenSSL.crypto.load_privatekey(
                                                OpenSSL.crypto.FILETYPE_PEM,
                                                open(keyfile).read())
            except:
                exit('{0}: ERROR: It seems that {1} is not a proper PEM-encoded SSL key.'.format(
                                                                datetime.datetime.now(),
                                                                keyfile))
        else:
            exit('{0}: ERROR: We need a key to generate a CSR!'.format(
                                                                datetime.datetime.now()))
    domain = (re.sub('^(https?|ftp)://([a-z0-9.-]+)/?.*$', '\g<2>',
                                                        conf['ipxe']['uri'],
                                                        flags=re.IGNORECASE)).lower()
    csr = OpenSSL.crypto.X509Req()
    csr.get_subject().CN = domain
    #req.get_subject().countryName = 'xxx'
    #req.get_subject().stateOrProvinceName = 'xxx'
    #req.get_subject().localityName = 'xxx'
    #req.get_subject().organizationName = 'xxx'
    #req.get_subject().organizationalUnitName = 'xxx'
    csr.set_pubkey(key)
    csr.sign(key, "sha512")
    with open('/tmp/main.csr', 'wb') as f:
        f.write(OpenSSL.crypto.dump_certificate_request(OpenSSL.crypto.FILETYPE_PEM, csr))
    return(csr)

def sslSign(conf, ca, key, csr):
    #ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca)
    #ca_key = OpenSSL.crypto.load_privatekey(key)
    #req = OpenSSL.crypto.load_certificate_request(csr)
    csr = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM,
                                                    open("/tmp/main.csr").read())
    cert = OpenSSL.crypto.X509()
    cert.set_subject(csr.get_subject())
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(24 * 60 * 60)
    cert.set_issuer(ca.get_subject())
    cert.set_pubkey(csr.get_pubkey())
    #cert.set_pubkey(ca.get_pubkey())
    cert.sign(key, "sha512")
    with open(conf['ipxe']['ssl_crt'], 'wb') as f:
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
    return(cert)

def sslPKI(conf):
    # run checks for everything, gen what's missing
    ssldir = conf['ipxe']['ssldir']
    os.makedirs(ssldir, exist_ok = True)
    certfile = conf['ipxe']['ssl_crt']
    key = sslCAKey(conf)
    ca = sslCA(conf, key = key)
    ckey = sslCKey(conf)
    if os.path.isfile(certfile):
        cert = OpenSSL.crypto.load_certificate(
                                        OpenSSL.crypto.FILETYPE_PEM,
                                        open(certfile).read())
        if not verifyCert(cert, ckey):
            csr = sslCSR(conf, ckey)
            cert = sslSign(conf, ca, key, csr)
    else:
        csr = sslCSR(conf, ckey)
        cert = sslSign(conf, ca, key, csr)
    return(cert)
