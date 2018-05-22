import os
import pprint
import re
import utils
import lxml.etree
from urllib.parse import urlparse

etree = lxml.etree
detect = utils.detect()
generate = utils.generate()
transform = utils.transform()
valid = utils.valid()

class Conf(object):
    def __init__(self, cfg, profile = None, validate = False):
        """
        A configuration object.

        Read a configuration file, parse it, and make it available to the rest
        of BDisk.

        Args:

        cfg           The configuration. Can be a filesystem path, a string,
                      bytes, or a stream. If bytes or a bytestream, it must be
                      in UTF-8 format.

        profile       (optional) A sub-profile in the configuration. If None
                        is provided, we'll first look for the first profile
                        named 'default' (case-insensitive). If one isn't found,
                        then the first profile found will be used. Can be a
                        string (in which we'll automatically search for the
                        given value in the "name" attribute) or a dict for more
                        fine-grained profile identification, such as:

                            {'name': 'PROFILE_NAME',
                             'id': 1,
                             'uuid': '00000000-0000-0000-0000-000000000000'}

                        You can provide any combination of these
                        (e.g. "profile={'id': 2, 'name' = 'some_profile'}").
        """
        self.xml_suppl = utils.xml_supplicant(cfg, profile = profile)
        self.xml = self.xml_suppl.xml
        for e in self.xml_suppl.xml.iter():
            self.xml_suppl.substitute(e)
        self.xml_suppl.get_profile(profile = self.xml_suppl.orig_profile)
        with open('/tmp/parsed.xml', 'wb') as f:
            f.write(lxml.etree.tostring(self.xml_suppl.xml))
        self.profile = self.xml_suppl.profile
        self.xsd = None
        self.cfg = {}
        #if validate:
            #if not self.validate():  # Need to write the XSD
            #    raise ValueError('The configuration did not pass XSD/schema '
            #                     'validation')

    def get_pki_obj(self, pki, pki_type):
        elem = {}
        if pki_type not in ('ca', 'client'):
            raise ValueError('pki_type must be "ca" or "client"')
        if pki_type == 'ca':
            elem['index'] = None
            elem['serial'] = None
        for e in pki.xpath('./*'):
            # These have attribs or children.
            if e.tag in ('cert', 'key', 'subject'):
                elem[e.tag] = {}
                if e.tag == 'subject':
                    for sub in e.xpath('./*'):
                        elem[e.tag][sub.tag] = transform.xml2py(sub.text,
                                                                attrib = False)
                else:
                    for a in e.xpath('./@*'):
                        elem[e.tag][a.attrname] = transform.xml2py(a)
                    elem[e.tag]['path'] = e.text
            else:
                elem[e.tag] = e.text
        return(elem)

    def get_source(self, source, item, _source):
        _source_item = {'flags': [],
                         'fname': None}
        elem = source.xpath('./{0}'.format(item))[0]
        if item == 'checksum':
            if elem.get('explicit', False):
                _explicit = transform.xml2py(
                        elem.attrib['explicit'])
                _source_item['explicit'] = _explicit
                if _explicit:
                    del(_source_item['fname'])
                    _source_item['value'] = elem.text
                    return(_source_item)
            else:
                _source_item['explicit'] = False
            if elem.get('hash_algo', False):
                _source_item['hash_algo'] = elem.attrib['hash_algo']
            else:
                _source_item['hash_algo'] = None
        if item == 'sig':
            if elem.get('keys', False):
                _keys = [i.strip() for i in elem.attrib['keys'].split(',')]
                _source_item['keys'] = _keys
            else:
                _source_item['keys'] = []
            if elem.get('keyserver', False):
                _source_item['keyserver'] = elem.attrib['keyserver']
            else:
                _source_item['keyserver'] = None
        _item = elem.text
        _flags = elem.get('flags', [])
        if _flags:
            for f in _flags.split(','):
                if f.strip().lower() == 'none':
                    continue
                _source_item['flags'].append(f.strip().lower())
        if _source_item['flags']:
            if 'regex' in _source_item['flags']:
                ptrn = _item.format(**self.xml_suppl.btags['regex'])
            else:
                ptrn = None
            _source_item['fname'] = detect.remote_files(
                    '/'.join((_source['mirror'],
                              _source['rootpath'])),
                    ptrn = ptrn,
                    flags = _source_item['flags'])
        else:
            _source_item['fname'] = _item
        return(_source_item)

    def get_xsd(self):
        path = os.path.join(os.path.dirname(__file__),
                            'bdisk.xsd')
        with open(path, 'r') as f:
            xsd = f.read()
        return(xsd)

    def parse_accounts(self):
        ## PROFILE/ACCOUNTS
        self.cfg['users'] = []
        # First we handle the root user, since it's a "special" case.
        _root = self.profile.xpath('./accounts/rootpass')
        self.cfg['root'] = transform.user(_root)
        for user in self.profile.xpath('./accounts/user'):
            _user = {'username': user.xpath('./username/text()')[0],
                     'sudo': transform.xml2py(user.attrib['sudo']),
                     'comment': None}
            _comment = user.xpath('./comment/text()')
            if len(_comment):
                _user['comment'] = _comment[0]
            _password = user.xpath('./password')
            _user.update(transform.user(_password))
            self.cfg['users'].append(_user)
        return()

    def parse_all(self):
        self.parse_profile()
        self.parse_meta()
        self.parse_accounts()
        self.parse_sources()
        self.parse_buildpaths()
        self.parse_pki()
        self.parse_gpg()
        self.parse_sync()
        return()

    def parse_buildpaths(self):
        ## PROFILE/BUILD(/PATHS)
        self.cfg['build'] = {'paths': {}}
        build = self.profile.xpath('./build')[0]
        _optimize = build.get('its_full_of_stars', 'no')
        self.cfg['build']['optimize'] = transform.xml2py(_optimize)
        for path in build.xpath('./paths/*'):
            self.cfg['build']['paths'][path.tag] = path.text
        self.cfg['build']['basedistro'] = build.get('basedistro', 'archlinux')
        # iso and ipxe are their own basic profile elements, but we group them
        # in here because 1.) they're related, and 2.) they're simple to
        # import. This may change in the future if they become more complex.
        ## PROFILE/ISO
        self.cfg['iso'] = {'sign': None,
                           'multi_arch': None}
        self.cfg['ipxe'] = {'sign': None,
                            'iso': None}
        for x in ('iso', 'ipxe'):
            # We enable all features by default.
            elem = self.profile.xpath('./{0}'.format(x))[0]
            for a in self.cfg[x]:
                self.cfg[x][a] = transform.xml2py(elem.get(a, 'yes'))
            if x == 'ipxe':
                self.cfg[x]['uri'] = elem.xpath('./uri/text()')[0]
        return()

    def parse_gpg(self):
        ## PROFILE/GPG
        self.cfg['gpg'] = {'keyid': None,
                           'gnupghome': None,
                           'publish': None,
                           'prompt_passphrase': None,
                           'keys': []}
        elem = self.profile.xpath('./gpg')[0]
        for attr in elem.xpath('./@*'):
            self.cfg['gpg'][attr.attrname] = transform.xml2py(attr)
        for key in elem.xpath('./key'):
            _key = {'algo': 'rsa',
                    'keysize': '4096',
                    'expire': '0',
                    'name': None,
                    'email': None,
                    'comment': None}
            for attr in key.xpath('./@*'):
                _key[attr.attrname] = transform.xml2py(attr)
            for param in key.xpath('./*'):
                _key[param.tag] = transform.xml2py(param.text, attrib = False)
            self.cfg['gpg']['keys'].append(_key)
        return()

    def parse_meta(self):
        ## PROFILE/META
        # Get the various meta strings. We skip regexes (we handle those
        # separately since they're unique'd per id attrib) and variables (they
        # are already substituted by self.xml_suppl.substitute(x)).
        _meta_iters = ('dev', 'names')
        for t in _meta_iters:
            self.cfg[t] = {}
            _xpath = './meta/{0}'.format(t)
            for e in self.profile.xpath(_xpath):
                for se in e:
                    if not isinstance(se, lxml.etree._Comment):
                        self.cfg[t][se.tag] = se.text
        for e in ('desc', 'uri', 'ver', 'max_recurse'):
            _xpath = './meta/{0}/text()'.format(e)
            self.cfg[e] = self.profile.xpath(_xpath)[0]
        # HERE is where we would handle regex patterns.
        # But we don't, because they're in self.xml_suppl.btags['regex'].
        #self.cfg['regexes'] = {}
        #_regexes = self.profile.xpath('./meta/regexes/pattern')
        #if len(_regexes):
        #    for ptrn in _regexes:
        #        self.cfg['regexes'][ptrn.attrib['id']] = re.compile(ptrn.text)
        return()

    def parse_pki(self):
        ## PROFILE/PKI
        self.cfg['pki'] = {'clients': []}
        elem = self.profile.xpath('./pki')[0]
        self.cfg['pki']['overwrite'] = transform.xml2py(
                                                elem.get('overwrite', 'no'))
        ca = elem.xpath('./ca')[0]
        clients = elem.xpath('./client')
        self.cfg['pki']['ca'] = self.get_pki_obj(ca, 'ca')
        for client in clients:
            self.cfg['pki']['clients'].append(self.get_pki_obj(client,
                                                               'client'))
        return()

    def parse_profile(self):
        ## PROFILE
        # The following are attributes of profiles that serve as identifiers.
        self.cfg['profile'] = {'id': None,
                               'name': None,
                               'uuid': None}
        for a in self.cfg['profile']:
            if a in self.profile.attrib:
                self.cfg['profile'][a] = self.profile.attrib[a]
        return()

    def parse_sources(self):
        ## PROFILE/SOURCES
        self.cfg['sources'] = []
        for source in self.profile.xpath('./sources/source'):
            _source = {}
            _source['arch'] = source.attrib['arch']
            _source['mirror'] = source.xpath('./mirror/text()')[0]
            _source['rootpath'] = source.xpath('./rootpath/text()')[0]
            # The tarball, checksum, and sig components requires some...
            # special care.
            for e in ('tarball', 'checksum', 'sig'):
                _source[e] = self.get_source(source, e, _source)
            self.cfg['sources'].append(_source)
        return()

    def parse_sync(self):
        ## PROFILE/SYNC
        self.cfg['sync'] = {}
        elem = self.profile.xpath('./sync')[0]
        # We populate defaults in case they weren't specified.
        for e in ('gpg', 'ipxe', 'iso', 'tftp'):
            self.cfg['sync'][e] = {'enabled': False,
                                   'path': None}
            sub = elem.xpath('./{0}'.format(e))[0]
            for a in sub.xpath('./@*'):
                self.cfg['sync'][e][a.attrname] = transform.xml2py(a)
            self.cfg['sync'][e]['path'] = sub.text
        rsync = elem.xpath('./rsync')[0]
        self.cfg['sync']['rsync'] = {'enabled': False}
        for a in rsync.xpath('./@*'):
            self.cfg['sync']['rsync'][a.attrname] = transform.xml2py(a)
        for sub in rsync.xpath('./*'):
            self.cfg['sync']['rsync'][sub.tag] = transform.xml2py(
                                                        sub.text,
                                                        attrib = False)
        return()

    def validate(self):
        self.xsd = etree.XMLSchema(self.get_xsd())
        return(self.xsd.validate(self.xml))