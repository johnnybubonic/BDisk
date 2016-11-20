#!/bin/bash

# Import settings.
if [[ -f /root/VARS.txt ]];
then
	source /root/VARS.txt
else
	# TODO: do these defaults via the config stuff in python instead.
	export DISTNAME='BDISK'
	export UXNAME='bdisk'
	export PNAME='BDisk'
	export DISTPUB='r00t^2'
	export DISTDESC='j00 got 0wnz0r3d lulz.'
	export REGUSR="${UXNAME}"
	export REGUSR_PASS=''
	export ROOT_PASS=''
fi

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
apacman -S --noconfirm --noedit --skipinteg --needed -S apacman apacman-deps apacman-utils expac
apacman --gendb
cleanPacorigs
# Install multilib-devel if we're in an x86_64 chroot.
if $(egrep -q '^\[multilib' /etc/pacman.conf);
then
	pacman --noconfirm -R gcc-libs libtool
	pacman --noconfirm -S --needed multilib-devel
	cleanPacorigs
	TGT_ARCH='x86_64'
else
	TGT_ARCH='i686'
fi
# Install some stuff we need for the ISO.
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/iso.pkgs.both | tr '\n' ' ')
if [[ -n "${PKGLIST}" ]];
then
	apacman --noconfirm --noedit --skipinteg -S --needed ${PKGLIST}
	apacman --gendb
	cleanPacorigs
fi
# And install arch-specific packages for the ISO, if there are any.
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/iso.pkgs.arch | tr '\n' ' ')
if [[ -n "${PKGLIST}" ]];
then
	apacman --noconfirm --noedit --skipinteg -S --needed ${PKGLIST}
	apacman --gendb
	cleanPacorigs
fi
# Do some post tasks before continuing
apacman --noconfirm --noedit -S --needed customizepkg-scripting
ln -s /usr/lib/libdialog.so.1.2 /usr/lib/libdialog.so
cleanPacorigs
apacman --noconfirm --noedit --skipinteg -S --needed linux
apacman --gendb
cp -a /boot/vmlinuz-linux /boot/vmlinuz-linux-${DISTNAME}
cp -af /boot/initramfs-linux.img /boot/initramfs-linux-${DISTNAME}.img
cleanPacorigs

# And install EXTRA functionality packages, if there are any.
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/packages.both | tr '\n' ' ')
if [[ -n "${PKGLIST}" ]];
then
	apacman --noconfirm --noedit --skipinteg -S --needed ${PKGLIST}
	apacman --gendb
	cleanPacorigs
fi
# Add the regular user
useradd -m -s /bin/bash -c "Default user" ${REGUSR}
usermod -aG users,games,video,audio ${REGUSR}
passwd -d ${REGUSR}
# Add them to sudoers
mkdir -p /etc/sudoers.d
chmod 750 /etc/sudoers.d
printf "Defaults:${REGUSR} \041lecture\n${REGUSR} ALL=(ALL) ALL\n" >> /etc/sudoers.d/${REGUSR}
# Set the password, if we need to.
if [[ -n "${REGUSR_PASS}" && "${REGUSR_PASS}" != 'BLANK' ]];
    then
      sed -i -e "s|^${REGUSR}::|${REGUSR}:${REGUSR_PASS}:|g" /etc/shadow
elif [[ "${REGUSR_PASS}" == '{[BLANK]}' ]];
then
	passwd -d ${REGUSR}
else
	usermod -L ${REGUSR}
fi
# Set the root password, if we need to.
if [[ -n "${ROOT_PASS}" && "${ROOT_PASS}" != 'BLANK' ]];
then
	sed -i -e "s|^root::|root:${ROOT_PASS}:|g" /etc/shadow
elif [[ "${ROOT_PASS}" == 'BLANK' ]];
then
	passwd -d root
else
	usermod -L root
fi
cleanPacorigs
cp -af /boot/initramfs-linux.img /boot/initramfs-linux-${DISTNAME}.img
# And install arch-specific extra packages, if there are any.
PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' /root/packages.arch | tr '\n' ' ')
if [[ -n "${PKGLIST}" ]];
then
	apacman --noconfirm --noedit --skipinteg -S --needed ${PKGLIST}
	apacman --gendb
	cleanPacorigs
fi
