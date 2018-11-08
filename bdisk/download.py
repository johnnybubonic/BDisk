import requests


class Download(object):
    def __init__(self, url, progress = True, offset = None, chunksize = 1024):
        self.cnt_len = None
        self.head = requests.head(url, allow_redirects = True).headers
        self.req_headers = {}
        self.range = False
        self.url = url
        self.offset = offset
        self.chunksize = chunksize
        self.progress = progress
        if 'accept-ranges' in self.head:
            if self.head['accept-ranges'].lower() != 'none':
                self.range = True
            if 'content-length' in self.head:
                try:
                    self.cnt_len = int(self.head['content-length'])
                except TypeError:
                    pass
            if self.cnt_len and self.offset and self.range:
                if not self.offset <= self.cnt_len:
                    raise ValueError(('The offset requested ({0}) is greater than '
                                      'the content-length value').format(self.offset, self.cnt_len))
                self.req_headers['range'] = 'bytes={0}-'.format(self.offset)

    def fetch(self):
        if not self.progress:
            self.req = requests.get(self.url, allow_redirects = True, headers = self.req_headers)
            self.bytes_obj = self.req.content
        else:
            self.req = requests.get(self.url, allow_redirects = True, stream = True, headers = self.req_headers)
            self.bytes_obj = bytes()
            _bytelen = 0
            # TODO: better handling for logging instead of print()s?
            for chunk in self.req.iter_content(chunk_size = self.chunksize):
                self.bytes_obj += chunk
                if self.cnt_len:
                    print('\033[F')
                    print('{0:.2f}'.format((_bytelen / float(self.head['content-length'])) * 100),
                          end = '%',
                          flush = True)
                    _bytelen += self.chunksize
                else:
                    print('.', end = '')
            print()
        return(self.bytes_obj)
