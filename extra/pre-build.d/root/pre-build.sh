#!/bin/bash

# Logging!
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>/var/log/chroot_install.log 2>&1

cleanPacorigs()
{
	for x in $(find /etc/ -type f -iname "*.pacorig");
	do
		mv -f ${x} ${x%%.pacorig}
	done
}

# NetworkManager is a scourge upon the earth that must be purged and cleansed.
ln -s /dev/null /etc/systemd/system/NetworkManager.service
ln -s /dev/null /etc/systemd/system/NetworkManager-dispatcher.service
# Build the keys
pacman-key --init
pacman-key --populate archlinux
pacman-key -r 93481F6B
# Update the mirror cache
pacman -Syy
# Just in case.
cleanPacorigs
# Install some prereqs
pacman -S --noconfirm --needed base syslinux wget rsync unzip jshon sed sudo abs xmlto bc docbook-xsl git
# And get rid of files it wants to replace
cleanPacorigs
# Force update all currently installed packages in case the tarball's out of date
pacman -Syyu --force --noconfirm
# And in case the keys updated...
pacman-key --refresh-keys
cleanPacorigs
# We'll need these.
pacman -S --noconfirm --needed base-devel
cleanPacorigs
# Install apacman
pacman --noconfirm -U /root/apacman*.tar.xz &&\
	 mkdir /var/tmp/apacman && chmod 0750 /var/tmp/apacman &&\
	 chown root:aurbuild /var/tmp/apacman
cleanPacorigs
apacman -S --noconfirm --noedit --skipinteg -S  apacman apacman-deps apacman-utils expac
apacman --gendb
cleanPacorigs
# Install multilib-devel if we're in an x86_64 chroot.
if $(egrep -q '^\[multilib' /etc/pacman.conf);
then
	pacman --noconfirm -R gcc-libs libtool
	pacman --noconfirm -S --needed multilib-devel
	TGT_ARCH='x86_64'
else
	TGT_ARCH='i686'
fi
# Install some stuff we need for the ISO.
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/prereqs/iso.pkgs.both | tr '\n' ' ')
cleanPacorigs
apacman --noconfirm --noedit --skipinteg -S --needed ${PKGLIST}
apacman --gendb
cleanPacorigs
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/prereqs/iso.pkgs.${TGT_ARCH} | tr '\n' ' ')

