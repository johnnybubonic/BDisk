function chroot_wrapper () {
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

  if [ -f "/usr/bin/systemd-nspawn" ];
  then
    CHROOTCMD="systemd-nspawn -D ${CHROOTDIR}"
  else
   CHROOTCMD="facehugger ${ARCHSUFFIX}"
  fi

  echo "NOW ENTERING ${CHROOTDIR}...."
  echo "_____________________________"
  ${CHROOTCMD}
  CHROOTDIR="${CHROOTDIR_GLOB}"
  BUILDDIR="${BUILDDIR_GLOB}"
}
