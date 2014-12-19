function holla_atcha_boi {
  # Do we have an existing chroot set up yet? If not, create.
  if [[ ! -d "root.x86_64/root" || ! -d "root.i686/root" ]];
  then
    echo "No existing chroot environment found. Creating..."
    rm -f ${LOCKFILE}
    ${BASEDIR}/lib/mk.chroot.sh
    touch ${LOCKFILE}
  fi
}

