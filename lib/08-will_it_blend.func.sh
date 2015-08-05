function will_it_blend () {

  FUNCNAME="will_it_blend"

  SQUASH_CMD="mksquashfs"
  SQUASH_OPTS="-noappend -comp xz"

  local ARCHSUFFIX="${1}"
  if [[ "${1}" == "64" ]]; 
  then
   local CHROOTDIR="${CHROOTDIR}root.x86_64"
   local BUILDDIR="${BUILDDIR}64"
   local AIROOT="x86_64"
   _CHROOT=${CHROOTDIR}
   _BUILD=${BUILDDIR}
   _AIROOT=${AIROOT}
  elif [[ "${1}" == "32" ]]; 
  then
   local CHROOTDIR="${CHROOTDIR}root.i686"
   local BUILDDIR="${BUILDDIR}32"
   local AIROOT="i686"
   _CHROOT=${CHROOTDIR}
   _BUILD=${BUILDDIR}
   _AIROOT=${AIROOT}
  else
   echo "WHOOPS. We hit an error that makes no logical sense."
   echo 'Dying.'
   exit 1
  fi

  if [[ "${I_AM_A_RACECAR}" == "y" ]]; 
  then
    RACECAR_CHK='nice -n -19 '
  else
    RACECAR_CHK=""
  fi

  if [ "${CHROOTDIR}/root/.bash_history" -nt "${ARCHBOOT}/${AIROOT}/airootfs.sfs" ] || [ ! -d "${BUILDDIR}/root/" ];
  then
   echo "Data is not sync'd to buildroot; syncing..."
   CHROOTDIR="${CHROOTDIR_GLOB}"
   BUILDDIR="${BUILDDIR_GLOB}"
   jenny_craig ${ARCHSUFFIX}
   CHROOTDIR="${_CHROOT}"
   BUILDDIR="${_BUILD}"
  fi
  echo "[${ARCHSUFFIX}-bit] Now generating the squashed image (if we need to) and hashes. This may take some time."
  BUILDDIR="${BUILDDIR_GLOB}"
  local BUILDDIR="${BUILDDIR}${ARCHSUFFIX}"

  # now let's build the squashed image... and generate some checksums as well to verify download integrity.
  # are we building split-arch ISOs? do we need the below?
  #if [[ "${MULTIARCH}" == "n" ]];
  #then
  # rm -rf ${ARCHBOOT}
  #fi
  mkdir -p ${ARCHBOOT}/${AIROOT}
  
  if [ ! -f "${ARCHBOOT}/${AIROOT}/airootfs.sfs" ] || [ "${CHROOTDIR}/root/.bash_history" -nt "${ARCHBOOT}/${AIROOT}/airootfs.sfs" ];
  then
   echo "[${ARCHSUFFIX}-bit] Squashing filesystem. This can take a while depending on the size of your chroot(s)."
   ${RACECAR_CHK}${SQUASH_CMD} ${BUILDDIR} ${ARCHBOOT}/${AIROOT}/airootfs.sfs ${SQUASH_OPTS} >> "${LOGFILE}.${FUNCNAME}" 2>&1
   cd ${ARCHBOOT}/${AIROOT}
   ${RACECAR_CHK}sha256sum airootfs.sfs >> airootfs.sha256
   ${RACECAR_CHK}md5sum airootfs.sfs >> airootfs.md5
   cd ${BASEDIR}
  else
   cd ${BASEDIR}
  fi

  # Generate the mtree spec.
  # Not really necessary anymore.
  #mtree -c -p ${BASEDIR}/chroot -K flags,gid,mode,nlink,uid,link,time,type > ${BASEDIR}/extra/mtree.spec

  # and now we copy stuff into the live directories
  echo "[${ARCHSUFFIX}-bit] Copying files for PXE, and ISO building, please be patient."
  #rm -rf ${TEMPDIR}/*
  cat ${BASEDIR}/extra/bdisk.png > ${BASEDIR}/extra/${UXNAME}.png
  cp -af ${BASEDIR}/extra/${UXNAME}.png ${TEMPDIR}/.
  cp -af ${BASEDIR}/extra/${UXNAME}.png ${TFTPDIR}/.
  mkdir -p ${TEMPDIR}/boot
  cp -af ${CHROOTDIR}/boot/initramfs-linux-${DISTNAME}.img ${TEMPDIR}/boot/${UXNAME}.${ARCHSUFFIX}.img
  cp -af ${CHROOTDIR}/boot/vmlinuz-linux-${DISTNAME} ${TEMPDIR}/boot/${UXNAME}.${ARCHSUFFIX}.kern
  cp -af ${CHROOTDIR}/boot/initramfs-linux-${DISTNAME}.img ${TFTPDIR}/${UXNAME}.${ARCHSUFFIX}.img
  cp -af ${CHROOTDIR}/boot/vmlinuz-linux-${DISTNAME} ${TFTPDIR}/${UXNAME}.${ARCHSUFFIX}.kern
  cp -af ${ARCHBOOT}/* ${HTTPDIR}/${DISTNAME}/.
  cp -af ${TFTPDIR}/* ${HTTPDIR}/.
  chown -R ${HTTPUSR}:${HTTPGRP} ${HTTPDIR}
  chown ${TFTPUSR}:${TFTPGRP} ${TFTPDIR}/${UXNAME}.*
}
