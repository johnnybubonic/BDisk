from setuptools import setup

import version

setup(name = 'bdisk',
      version = version.BDISK_VERSION,
      description = ('An easy liveCD creator built in python. Supports hybrid '
                     'ISOs/USB, iPXE, and UEFI.'),
      url = 'https://bdisk.square-r00t.net',
      project_urls={'Bug Tracker': ('https://bugs.square-r00t.net/'
                                    'index.php?project=2&do=index'),
                    'Documentation': 'https://bdisk.square-r00t.net/',
                    'Source Code': 'https://git.square-r00t.net/BDisk/'}
      author = 'Brent Saner',
      author_email = 'bts@square-r00t.net',
      license = 'GPLv3',
      packages = ['bdisk'],
      platforms = ['linux'],
      classifiers = ['Environment :: Console',
                     'Intended Audience :: End Users/Desktop',
                     'Intended Audience :: Information Technology',
                     'Intended Audience :: System Administrators',
                     'Operating System :: POSIX :: Linux'],
      zip_safe = False)
