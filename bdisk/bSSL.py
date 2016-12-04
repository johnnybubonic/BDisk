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
        exit(("{0}: Key does not match certificate!".format(datetime.datetime.now())))
    else:
        print("{0}: Key verified against certificate successfully.".format(datetime.datetime.now()))
    # This is disabled because there doesn't seem to currently be any way
    # to actually verify certificates against a given CA.
    #if CA:
    #    try:
    #        magic stuff here

def sslCAKey():
    key = OpenSSL.crypto.PKey()
    print("{0}: Generating SSL CA key...".format(datetime.datetime.now()))
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
    #print OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
    return(key)

def sslCA(conf, key = None):
    if not key:
        try:
            key = conf['ipxe']['ssl_cakey']
        except:
            exit("{0}: Cannot find a valid CA Key to use.".format(datetime.datetime.now()))
    domain = (re.sub('^(https?|ftp)://([a-z0-9.-]+)/?.*$', '\g<2>',
                        conf['ipxe']['uri'],
                        flags=re.IGNORECASE)).lower()
    # http://www.pyopenssl.org/en/stable/api/crypto.html#pkey-objects
    # http://docs.ganeti.org/ganeti/2.14/html/design-x509-ca.html
    ca = OpenSSL.crypto.X509()
    ca.set_version(3)
    ca.set_serial_number(1)
    ca.get_subject().CN = domain
    ca.gmtime_adj_notBefore(0)
    # valid for ROUGHLY 10 years. years(ish) * days * hours * mins * secs.
    # the paramater is in seconds, which is why we need to multiply them all together.
    ca.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  
    ca.set_issuer(ca.get_subject())
    ca.set_pubkey(key)
    ca.add_extensions([
            OpenSSL.crypto.X509Extension("basicConstraints",
                                        True,
		    	                "CA:TRUE, pathlen:0"),
            OpenSSL.crypto.X509Extension("keyUsage",
                                        True,
                                        "keyCertSign, cRLSign"),
            OpenSSL.crypto.X509Extension("subjectKeyIdentifier",
                                        False,
                                        "hash",
                                        subject = ca),])
    ca.sign(key, "sha512")
    #print OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca)
    return(ca)

def sslCKey():
    key = OpenSSL.crypto.PKey()
    print("{0}: Generating SSL Client key...".format(datetime.datetime.now()))
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
    #print OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
    return(key)

def sslCSR(conf, key):
    domain = (re.sub('^(https?|ftp)://([a-z0-9.-]+)/?.*$', '\g<2>',
                        conf['ipxe']['uri'],
                        flags=re.IGNORECASE)).lower()
    csr = OpenSSL.crypto.X509Req()
    csr.get_subject().CN = domain
    csr.set_pubkey(key)
    csr.sign(key, "sha512")
    #print OpenSSL.crypto.dump_certificate_request(OpenSSL.crypto.FILETYPE_PEM, req)
    return(csr)

def sslSign(ca, key, csr):
    ca_cert = OpenSSL.crypto.load_certificate(ca)
    ca_key = OpenSSL.crypto.load_privatekey(key)
    req = OpenSSL.crypto.load_certificate_request(csr)
    cert = OpenSSL.crypto.X509()
    cert.set_subject(req.get_subject())
    cert.set_serial_number(1)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(24 * 60 * 60)
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(ca_key, "sha512")
    #print OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    return(cert)
