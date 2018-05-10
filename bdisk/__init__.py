import os
import platform
import sys

"""
BDisk - An easy liveCD creator built in python.
"""

# BDisk is only supported on Python 3.4 and up.
if sys.version_info.major != 3:
    raise RuntimeError('BDisk is only supported on Python 3')
elif sys.version_info.minor <= 3:
    raise RuntimeError('BDisk is only supported on Python 3.4 and up')

# BDisk is only supported on GNU/Linux. There *might* be a way to make it work
# with certain *BSDs, but if that's possible at all it'll have to come at a
# later date. Patches welcome.
# I'd have to find out how to manipulate/create FAT filesystems and such as
# well.
# I'd be curious to see if I can get it working in Cygwin or WSL:
# https://docs.microsoft.com/en-us/windows/wsl/install-win10
# And maybe, if we're really pie-in-the-sky, macOS's Fink/Homebrew/Macports.
if platform.system() != 'Linux':
    raise RuntimeError('BDisk is currently only supported on GNU/Linux')

# CURRENTLY, we require root user because of the chroots and such. However,
# there should be creative ways to do this with cgroups as a regular user in
# the future. Patches welcome (or at least some input).
if os.geteuid() != 0:
    raise PermissionError('BDisk currently requires root privileges')
