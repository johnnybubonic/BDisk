function facehugger () {
  local ARCHSUFFIX="${1}"
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
 
  echo "Creating manual chroot mountpoints."
  # Latch on and inject ourself into the environment. Get it?
  mount -t proc -o nosuid,noexec,nodev proc ${CHROOTDIR}/proc &&
  mount -t sysfs -o nosuid,noexec,nodev,ro sys ${CHROOTDIR}/sys &&
  if [ -d /sys/firmware/efi/efivars ];
  then
    mount -t efivarfs -o nosuid,noexec,nodev efivarfs ${CHROOTDIR}/sys/firmware/efi/efivars
  fi &&
  mount -t devtmpfs -o mode=0755,nosuid udev ${CHROOTDIR}/dev &&
  mount -t devpts -o mode=0620,gid=5,nosuid,noexec devpts ${CHROOTDIR}/dev/pts &&
  mount -t tmpfs -o mode=1777,nosuid,nodev shm ${CHROOTDIR}/dev/shm &&
  mount -t tmpfs -o nosuid,nodev,mode=0755 run ${CHROOTDIR}/run &&
  mount -t tmpfs -o mode=1777,strictatime,nodev,nosuid tmp ${CHROOTDIR}/tmp
  echo "======================"
  echo "NOW ENTERING CHROOT..."
  echo "======================"
  chroot ${CHROOTDIR} /bin/bash
  rm -f ${CHROOTDIR}/root/chroot
  CHROOTDIR="${CHROOTDIR_GLOB}"
  BUILDDIR="${BUILDDIR_GLOB}"
  release_me ${ARCHSUFFIX}
}

