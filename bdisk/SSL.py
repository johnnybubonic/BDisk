import OpenSSL
# https://cryptography.io/en/latest/x509/reference/#cryptography.x509.CertificateBuilder.sign
# migrate old functions of bSSL to use cryptography
# but still waiting on their recpipes.
# https://cryptography.io/en/latest/x509/tutorial/
#import OpenSSL
#k = OpenSSL.crypto.PKey()
#k.generate_key(OpenSSL.crypto.TYPE_RSA, 4096)
#x = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM,
#                                   k,
#                                   cipher = 'aes256',
#                                   passphrase = 'test')