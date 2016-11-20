import os
import sys
import platform

def getOS():
    # Returns one of: SuSE, debian, fedora, redhat, centos, mandrake,
    # mandriva, rocks, slackware, yellowdog, gentoo, UnitedLinux,
    # turbolinux, arch, mageia
    distro = list(platform.linux_distribution())[0].lower()
    return(distro)

def getBits():
    bits = list(platform.architecture())[0]
    return(bits)
