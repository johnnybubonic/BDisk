function jenny_craig () {
  BUILDDIR="${BUILDDIR_GLOB}"
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

  local _CURDIR=$(pwd)
  echo "Syncing important files to ${BUILDDIR} for building the squashed filesystem (this may take some time)..."

  # we have to do this or else the package management from LIVE doesn't really work too hot.
  cd ${CHROOTDIR}/var/lib/pacman
  echo "Compressing the package DB..."
  #rm -f ${CHROOTDIR}/usr/local/pacman.db.tar.xz
  tar -cf - local | xz -c9 > ../../../usr/local/pacman.db.tar.xz
  cd ${_CURDIR}

  # sync over new changes and trim out the fat
  rsync -a --delete ${CHROOTDIR}/. ${BUILDDIR}/.
  set +e
  cp -af ${BUILDDIR}/usr/share/zoneinfo/EST5EDT ${BUILDDIR}/etc/localtime > /dev/null 2>&1
  cp -af ${CHROOTDIR}/usr/share/zoneinfo/EST5EDT ${CHROOTDIR}/etc/localtime > /dev/null 2>&1
  set -e
  cp -af ${BUILDDIR}/usr/share/locale/locale.alias ${BUILDDIR}/tmp/.
  echo "Cleaning up unnecessary cruft in ${BUILDDIR}..."

  rm -f ${BUILDDIR}/root/.bash_history
  rm -f ${BUILDDIR}/root/.viminfo
  #rm -f ${BUILDDIR}/etc/localtime
  rm -f ${BUILDDIR}/root/.bashrc
  # DISABLE when no longer building custom kernel
  find ${BUILDDIR}/usr/lib/modules/ -maxdepth 1 -iname "*-ARCH" -exec rm -rf '{}' \;
  find ${BUILDDIR}/ -type f -name "*.pacnew" -exec rm -rf '{}' \;
  sed -i -e '/^MAKEFLAGS=.*$/d' ${BUILDDIR}/etc/makepkg.conf
  rm -rf ${BUILDDIR}/usr/share/locale/*
  mv -f ${BUILDDIR}/tmp/locale.alias ${BUILDDIR}/usr/share/locale/.
  rm -rf ${BUILDDIR}/var/cache/pacman/*
  rm -rf ${BUILDDIR}/var/cache/pkgfile/*
  rm -rf ${BUILDDIR}/var/cache/apacman/pkg/*
  rm -rf ${BUILDDIR}/var/lib/pacman/*
  mkdir -p ${BUILDDIR}/var/lib/pacman/local
  rm -rf ${BUILDDIR}/var/abs/local/yaourtbuild/*
  rm -rf ${BUILDDIR}/usr/share/zoneinfo
  rm -rf ${BUILDDIR}/tmp/*
  rm -rf ${BUILDDIR}/var/tmp/*
  rm -rf ${BUILDDIR}/var/abs/*
  rm -rf ${BUILDDIR}/run/*
  rm -rf ${BUILDDIR}/boot/*
  #rm -rf ${BUILDDIR}/root/*
  rm -rf ${BUILDDIR}/root/post-build.sh
  rm -rf ${BUILDDIR}/usr/src/*
  rm -rf ${BUILDDIR}/var/log/*
  rm -rf ${BUILDDIR}/.git
  CHROOTDIR="${CHROOTDIR_GLOB}"
  BUILDDIR="${BUILDDIR_GLOB}"
}

