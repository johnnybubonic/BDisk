# These are *key* ciphers, for encrypting exported keys.
openssl_ciphers = ['aes128', 'aes192', 'aes256', 'bf', 'blowfish',
                   'camellia128', 'camellia192', 'camellia256', 'cast', 'des',
                   'des3', 'idea', 'rc2', 'seed']
# These are *hash algorithms* for cert digests.
openssl_digests = ['blake2b512', 'blake2s256', 'gost', 'md4', 'md5', 'mdc2',
                   'rmd160', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']

class PromptStrings(object):
    gpg = {
        'attribs': {
            'algo': {
                'text': 'the subkey\'s encryption type/algorithm',
                # The following can ONLY be used for encryption, not signing: elg, cv
                #'choices': ['rsa', 'dsa', 'elg', 'ed', 'cv', 'nistp', 'brainpool.1', 'secp.k1'],
                'choices': ['rsa', 'dsa', 'ed', 'nist', 'brainpool.1', 'sec.k1'],
                #'default': 'rsa'
                'default': 'ed'
                },
            'keysize': {
                'text': 'the subkey\'s key size (in bits)',
                'choices': {
                    'rsa': ['1024', '2048', '4096'],
                    'dsa': ['768', '2048', '3072'],
                    #'elg': ['1024', '2048', '4096'],  # Invalid for signing, etc.
                    'ed': ['25519'],
                    #'cv': ['25519'],
                    'nistp': ['256', '384', '521'],
                    'brainpool.1': ['256', '384', '512'],
                    'sec.k1': ['256']
                    },
                'default': {
                    'rsa': '4096',
                    'dsa': '3072',
                    'ed': '25519',
                    'nistp': '521',
                    'brainpool.1': '512',
                    'sec.k1': '256'
                    }
                }
            },
        'params': ['name', 'email', 'comment']
        }
    ssl = {
        'attribs': {
            'cert': {
                'hash_algo': {
                    'text': ('What hashing algorithm do you want to use? '
                             '(Default is sha512.)'),
                    'prompt': 'Hashing algorithm: ',
                    'options': openssl_digests,
                    'default': 'aes256'
                    }
                },
            'key': {
                'cipher': {
                    'text': ('What encryption algorithm/cipher do you want to '
                             'use? (Default is aes256.) Use "none" to specify '
                             'a key without a passphrase.'),
                    'prompt': 'Cipher: ',
                    'options': openssl_ciphers + ['none'],
                    'default': 'aes256'
                    },
                'keysize': {
                    'text': ('What keysize/length (in bits) do you want the '
                             'key to be? (Default is 4096; much higher values '
                             'are possible but are untested and thus not '
                             'supported by this tool; feel free to edit the '
                             'generated configuration by hand.) (If the key '
                             'cipher is "none", this is ignored.)'),
                    'prompt': 'Keysize: ',
                    # TODO: do all openssl_ciphers support these sizes?
                    'options': ['1024', '2048', '4096'],
                    'default': 'aes256'
                    },
                'passphrase': {
                    'text': ('What passphrase do you want to use for the key? '
                             'If you specified the cipher as "none", this is '
                             'ignored (you can just hit enter).'),
                    'prompt': 'Passphrase (will not echo back): ',
                    'options': None,
                    'default': ''
                    }
                }
            },
        'paths': {
            'cert': '(or read from) the certificate',
            'key': '(or read from) the key',
            'csr': ('(or read from) the certificate signing request (if '
                    'blank, we won\'t write to disk - the operation will '
                    'occur entirely in memory assuming we need to generate/'
                    'sign)')
            },
        'paths_ca': {
            'index': ('(or read from) the CA (Certificate Authority) Database '
                      'index file (if left blank, one will not be used)'),
            'serial': ('(or read from) the CA (Certificate Authority) '
                       'Database serial file (if left blank, one will not be '
                       'used)'),
            },
        'subject': {
            'countryName': {
                'text': ('the 2-letter country abbreviation (must conform to '
                         'ISO3166 ALPHA-2)?\n'
                         'Country code: ')
                },
            'localityName': {
                'text': ('the city/town/borough/locality name?\n'
                         'Locality: ')
                },
            'stateOrProvinceName': {
                'text': ('the state/region name (full string)?\n'
                        'Region: ')
                },
            'organization': {
                'text': ('your organization\'s name?\n'
                         'Organization: ')
                },
            'organizationalUnitName': {
                'text': ('your department/role/team/department name?\n'
                         'Organizational Unit: ')
                },
            'emailAddress': {
                'text': ('the email address to be associated with this '
                         'certificate/PKI object?\n'
                         'Email: ')
                }
            }
        }
