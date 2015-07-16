function centos_is_stupid {

  FUNCNAME="centos_is_stupid"

  rpm -qa | egrep "^xorriso-[0-9]" > /dev/null 2>&1
  if [[ "${?}" != "0" ]];
  then
    # Download/install the proper xorriso
    EL_VER="$(rpm -qa coreutils | sed -re 's/^coreutils-[0-9.-]*el([0-9])*.*$/\1/g')"
    if (("${EL_VER}" < "7"));
    then
      echo "Wow. Your CentOS/RHEL is too old. Sorry; this is only supported on CentOS/RHEL 7 and up."
      exit 1
    fi
    XORRISO_RPM=$(curl -s http://pkgs.repoforge.org/xorriso/ | egrep "\"xorriso-[0-9.-]*el${EL_VER}.rf.x86_64.rpm\"" | sed -re "s/^.*\"(xorriso[0-9.-]*el${EL_VER}.rf.x86_64.rpm).*$/\1/g")
    echo "Since you're using either CentOS or RHEL, we need to install xorriso directly from an RPM. Please wait while we do this..."
    curl -sLo /tmp/${XORRISO_RPM} http://pkgs.repoforge.org/xorriso/${XORRISO_RPM}
    yum -y install /tmp/${XORRISO_RPM} >> "${LOGFILE}.${FUNCNAME}" 2>&1
    echo "Done."
    echo
  fi
  # We used to fetch and compile mksquashfs from source here, but no longer- because a new enough version is *finally* in CentOS repos as of CentOS 7.

}
