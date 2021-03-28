import hashlib
import importlib  # needed for the guest-os-specific stuff...
import os
from . import utils
from urllib.parse import urljoin


def hashsum_downloader(url, filename = None):
    # TODO: support "latest" and "regex" flags? or remove from specs (since the tarball can be specified by these)?
    # move that to the utils.DOwnload() class?
    d = utils.Download(url, progress = False)
    hashes = {os.path.basename(k):v for (v, k) in [line.split() for line in d.fetch().decode('utf-8').splitlines()]}
    if filename:
        if filename in hashes:
            return(hashes[filename])
        else:
            raise KeyError('Filename {0} not in the list of hashes'.format(filename))
    return(hashes)


class Prepper(object):
    def __init__(self, dirs, sources, gpg = None):
        # dirs is a ConfParse.cfg['build']['paths'] dict of dirs
        self.CreateDirs(dirs)
        # TODO: set up GPG env here so we can use it to import sig key and verify sources
        for idx, s in enumerate(sources):
            self._download(idx)

    def CreateDirs(self, dirs):
        for d in dirs:
            os.makedirs(d, exist_ok = True)
        return()


    def _download(self, source_idx):
        download = True
        _source = self.cfg['sources'][source_idx]
        _dest_dir = os.path.join(self.cfg['build']['paths']['cache'], source_idx)
        _tarball = os.path.join(_dest_dir, _source['tarball']['fname'])
        _remote_dir = urljoin(_source['mirror'], _source['rootpath'])
        _remote_tarball = urljoin(_remote_dir + '/', _source['tarball']['fname'])
        def _hash_verify():  # TODO: move to utils.valid()?
            # Get a checksum.
            if 'checksum' in _source:
                if not _source['checksum']['explicit']:
                    _source['checksum']['value'] = hashsum_downloader(urljoin(_remote_dir + '/',
                                                                              _source['checksum']['fname']))
                if not _source['checksum']['hash_algo']:
                    _source['checksum']['hash_algo'] = utils.detect.any_hash(_source['checksum']['value'],
                                                                             normalize = True)[0]
                _hash = hashlib.new(_source['checksum']['hash_algo'])
                with open(_tarball, 'rb') as f:
                    # It's potentially a large file, so we chunk it 64kb at a time.
                    _hashbuf = f.read(64000)
                    while len(_hashbuf) > 0:
                        _hash.update(_hashbuf)
                        _hashbuf = f.read(64000)
                if _hash.hexdigest().lower() != _source['checksum']['value'].lower():
                    return(False)
            return(True)
        def _sig_verify(gpg_instance):  # TODO: move to utils.valid()? or just use as part of the bdisk.GPG module?
            pass
        if os.path.isfile(_tarball):
            download = _hash_verify()
            download = _sig_verify()
        if download:
            d = utils.Download(_remote_tarball)
