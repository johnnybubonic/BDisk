#!/bin/bash

# A lot of snippets, inspiration, and some config directives are from https://projects.archlinux.org/archiso.git/ / the ArchLinux ISO layout.
# Many thanks and praise are deserved.


#DEBUG
#set -x

echo "Starting at $(date)..."

## Import settings
if [ -f "build.conf" ];
then
 echo "Now importing settings/variables."
 set -e
 source extra/build.conf.sample
 source build.conf
 set +e
else
 echo "You have not configured a build.conf OR you are not running from the project's root directory (the git repository's working directory).
 If you are indeed in the correct directory, you may copy the sample at extra/build.conf.sample,
 edit it for appropriate values, and copy to <PROJECT ROOT>/build.conf"
 echo 'For now, though, I am using the defaults. If the build fails complaining about a'
 echo 'missing http user, you need to specify a custom/distro-pertinent one.'
 cp extra/build.conf.sample build.conf
 set -e
 source extra/build.conf.sample
 set +e
fi
 

## PREPARATION ##

# safemode browsing enabled. lolz
set -e

# do some basic error checking
ARCH=$(uname -m)

if [[ ${EUID} -ne 0 ]];
then
  #echo "This script must be run as root" 1>&2
  echo "This script must be run as root."
  exit 1
elif [ -f ${LOCKFILE} ];
then
  echo "Script already running, stale lockfile present, or an error occurred during last run."
  echo "Please clear ${LOCKFILE} by hand before attempting another build."
  echo -n "Timestamp of lockfile is: "
  ls -l ${LOCKFILE} | awk '{print $6" "$7" "$8}'
  exit 1
elif [[ "$(uname -s)" != "Linux" ]];
then
  echo "ERROR: This script is only supported on GNU/Linux."
  exit 1
elif [[ "${ARCH}" != 'x86_64' ]];
then
  echo "Your hardware architecture, ${ARCH}, is not supported. Only x86_64 is supported."
  echo "Dying now."
  exit 1
fi

echo "Checking directory structure and creating lockfile at ${LOCKFILE}..."
touch ${LOCKFILE}

# make sure the paths exist and then check for an existing chroot session
for i in ${BASEDIR} ${CHROOTDIR32} ${CHROOTDIR64} ${BUILDDIR}32 ${BUILDDIR}64 ${ISODIR} ${MOUNTPT} ${TEMPDIR}/{${UXNAME},${DISTNAME}} ${ARCHBOOT} ${SRCDIR} ${TFTPDIR} ${HTTPDIR}/${DISTNAME} ${BASEDIR}/logs;
do
 if [ ! -d ${i} ];
 then
  #echo "${i} does not exist - creating."
  mkdir -p ${i}
 fi
done

if [ ! -f "./BUILDNO" ];
then
 echo '0' > ./BUILDNO
fi

CHROOTDIR_GLOB="${CHROOTDIR}"
BUILDDIR_GLOB="${BUILDDIR}"

# Set the version.
VERSION="$(git describe --abbrev=0 --tags)-$(git rev-parse --short --verify HEAD)"
BUILD="$(cat BUILDNO)"
BUILD="$(expr ${BUILD} + 1)"
echo ${BUILD} > ./BUILDNO
BUILDTIME="$(date)"
BUILD_MACHINE="$(hostname -f)"
#BUILD_USERNAME="${SUDO_USER}"
#BUILD_USERNAME="$(who am i | awk '{print $1}')"
set +e ; logname > /dev/null 2>&1
if [[ "${?}" == "0" ]];
then
 BUILD_USERNAME="$(logname)"
else
 BUILD_USERNAME="$(whoami)"
fi
set -e
USERNAME_REAL="$(grep ${BUILD_USERNAME} /etc/passwd | cut -f5 -d':')"

cat > VERSION_INFO.txt << EOF
Version:	${VERSION}
Build:		${BUILD}
Time:		${BUILDTIME}
Machine:	${BUILD_MACHINE}
User:		${BUILD_USERNAME} (${USERNAME_REAL})
EOF

## FUNCTIONS ##

source lib/00-depcheck.func.sh
source lib/02-im_batman.func.sh
source lib/03-holla_atcha_boi.func.sh
source lib/04-release_me.func.sh
source lib/05-facehugger.func.sh
source lib/06-chroot_wrapper.func.sh
source lib/07-jenny_craig.func.sh
source lib/08-centos_is_stupid.func.sh
source lib/09-will_it_blend.func.sh
source lib/10-stuffy.func.sh
source lib/11-yo_dj.func.sh
source lib/12-mentos.func.sh

## The Business-End(TM) ##

CHROOTDIR="${CHROOTDIR_GLOB}"
BUILDDIR="${BUILDDIR_GLOB}"
holla_atcha_boi

rm -rf ${TEMPDIR}/*
release_me 64 > /dev/null 2>&1
release_me 32 > /dev/null 2>&1

# do we need to perform any updates?
if [[ -f "${CHROOTDIR}root.x86_64/root/chroot" || -f "${CHROOTDIR}root.i686/root/chroot" ]];
then
  chroot_wrapper 64
  chroot_wrapper 32
  centos_is_stupid
  will_it_blend 64
  will_it_blend 32
  yo_dj
fi

if [[ ${1} == "update" ]];
then
  mentos
  centos_is_stupid
  will_it_blend 32
  will_it_blend 64
  yo_dj
fi

# or do we want to just chroot in?
if [[ ${1} == "chroot" ]]; 
then
  chroot_wrapper 64
  chroot_wrapper 32
  rm -f ${LOCKFILE}
  exit 0
fi

# or are we just building?
if [[ ${1} == "build" ]] || [ -z ${1} ] || [[ ${1} == "all" ]];
then
  if [[ "${MULTIARCH}" == "y" ]];
  then
    centos_is_stupid
    will_it_blend 64
    will_it_blend 32
    yo_dj any
  else
    centos_is_stupid
    will_it_blend 64
    yo_dj 64
    centos_is_stupid
    will_it_blend 32
    yo_dj 32
  fi
fi

# clean up, clean up, everybody, everywhere
echo "Cleaning up some stuff leftover from the build..."
#rm -rf ${TEMPDIR}/*
#rm -rf ${SRCDIR}/*
cd ${BASEDIR}

if [[ "${GIT}" == "yes" ]];
then
  echo "Committing changes to git..."
  git add --all .
  git commit -m "post-build at $(date)"
fi

# yay! we're done!
rm -f ${LOCKFILE}
echo "Finished successfully at $(date)!"
