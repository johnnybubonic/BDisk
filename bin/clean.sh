#!/bin/bash

echo "Started at $(date)..."

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
 echo "If you are indeed in the correct directory, you may copy the sample at ../extra/build.conf.sample,
 echo "edit it for appropriate values, and copy to <PROJECT ROOT>/build.conf"
 echo
 echo 'This error is fatal. Dying.'
 exit 1
fi

if [[ ${EUID} -ne 0 ]];
then
  #echo "This script must be run as root" 1>&2
  echo "This script must be run as root."
  echo
  exit 1
elif [ -f ${LOCKFILE} ];
then
  echo "Script already running, stale lockfile present, or an error occurred during last run."
  echo "Please clear ${LOCKFILE} by hand before attempting another build."
  echo -n "Timestamp of lockfile is: "
  ls -l ${LOCKFILE} | awk '{print $6" "$7" "$8}'
  exit 1
fi

echo "Creating lockfile at ${LOCKFILE}..."
touch ${LOCKFILE}

if [[ "${1}" == "all" ]];
then
 DIRS="${CHROOTDIR}root.i686 ${CHROOTDIR}root.x86_64 ${BUILDDIR}32 ${BUILDDIR}64 ${ISODIR} ${TEMPDIR} ${ARCHBOOT} ${SRCDIR} ${TFTPDIR} ${HTTPDIR} ${BASEDIR}/logs"
 FILES="latest.32.tar.gz latest.64.tar.gz"
elif [[ "${1}" == "chroot" ]];
then
 DIRS="${CHROOTDIR}root.i686 ${CHROOTDIR}root.x86_64 ${BUILDDIR}32 ${BUILDDIR}64 ${ISODIR} ${TEMPDIR} ${ARCHBOOT} ${SRCDIR} ${TFTPDIR} ${HTTPDIR}"
 FILES=""
elif [[ "${1}" == "squash" ]];
then
 DIRS="${BUILDDIR}32 ${BUILDDIR}64 ${ISODIR} ${TEMPDIR} ${ARCHBOOT} ${SRCDIR} ${TFTPDIR} ${HTTPDIR}"
 FILES=""
else
 DIRS="${ISODIR} ${TEMPDIR} ${ARCHBOOT} ${SRCDIR} ${TFTPDIR} ${HTTPDIR}"
 FILES=""
fi

echo "I will be deleting the contents of: ${DIRS}"
echo "I will be deleting the files: ${FILES}"
read -p 'Do you wish to continue? [Y/n] ' CONFIRM

if [ -z "${CONFIRM}" ];
then
 CONFIRM="y"
fi

CONFIRM=${CONFIRM:0:1}
CONFIRM=$(echo ${CONFIRM} | tr [[:upper:]] [[:lower:]])

if [[ "${CONFIRM}" != "y" ]];
then
 echo 'Exiting.'
 exit 0
fi


for i in "${DIRS}";
do
 rm -rf ${i}/*
done

for i in "${FILES}";
do
 rm -f ${i}
done

rm -f ${LOCKFILE}

echo "Finished successfully at $(date)!"
