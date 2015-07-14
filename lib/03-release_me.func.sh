function release_me () {
  ## check for mountpoints from a manual chroot and umount them if they're still mounted.
  ## NOTE: you can use findmnt(8) to view a tree of mountpoints, including bindmounts etc.
  # Is there an active chroot?
  set +e
  if [[ "${1}" == "64" ]];
  then
   local CHROOTDIR="${CHROOTDIR}root.x86_64"
   local BUILDDIR="${BUILDDIR}64"
  elif [[ "${1}" == "32" ]];
  then
   local CHROOTDIR="${CHROOTDIR}root.i686"
   local BUILDDIR="${BUILDDIR}32"
  else
   echo "WHOOPS. We hit an error that makes no logical sense."
   echo 'Dying.'
   exit 1
  fi

  echo "Checking for and cleaning up mountpoints from the chroot environment..."
  for i in tmp run dev/shm dev/pts dev
  do
      umount -l ${CHROOTDIR}/${i}
  done
  # and is it using efivars?
  if [ -d ${CHROOTDIR}/sys/firmware/efi/efivars ];
  then
    umount -l ${CHROOTDIR}/sys/firmware/efi/efivars
  fi
  # and finish cleaning up normal chroots
  for i in sys proc
  do
      umount -l ${CHROOTDIR}/${i}
  done 
  # and is it mounted via two mountpoints a la arch-chroot?
  mount | awk '{print $3}' | grep -q ${MOUNTPT}
  if [[ ${?} == "0" ]];
  then
    umount ${MOUNTPT}
  fi
  if [ -d ${SRCDIR}/efiboot ];
  then
    umount -l ${SRCDIR}/efiboot
  fi
  rm -rf ${SRCDIR}/efiboot
  #rm -rf ${TEMPDIR}/*
  set -e # and go back to failing on non-0 exit status.
  CHROOTDIR="${CHROOTDIR_GLOB}"
  BUILDDIR="${BUILDDIR_GLOB}"
}
