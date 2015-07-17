function centos_is_stupid {

  FUNCNAME="centos_is_stupid"

  if [[ "${HOST_DIST}" == "CentOS" || "${HOST_DIST}" == "RHEL" ]];
  then
    rpm -qa | egrep -q "^xorriso-[0-9]"
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
    # This also lets us cut out the crufty version check and replace it with the one above.
  fi

  # UGH. And you know what? Fuck SUSE too.
  if [[ "${HOST_DIST}" == "openSUSE" || "${HOST_DIST}" == "SUSE" ]];
  then
    rpm -qa | egrep -q "^xorriso-[0-9]"
    if [[ "${?}" != "0" ]];
    then
      # Download/install the proper xorriso
      source /etc/os-release
      SUSE_VER="${VERSION_ID}"
      XORRISO_RPM=$(curl -s "http://software.opensuse.org/download.html?project=home%3AKnolleblau&package=xorriso" | egrep "/openSUSE_${SUSE_VER}/x86_64/xorriso-[0-9.-]" | tail -n1 | sed -re 's|^.*x86_64/(xorriso-[0-9.-]*.x86_64.rpm).*$|\1|g')
      echo "Since you're using openSUSE or SLED/SLES, we need to install xorriso directly from an RPM. Please wait while we do this..."
      curl -sLo /tmp/${XORRISO_RPM} "http://download.opensuse.org/repositories/home:/Knolleblau/openSUSE_${SUSE_VER}/x86_64/${XORRISO_RPM}"
      zypper install --no-confirm -l /tmp/${XORRISO_RPM} >> "${LOGFILE}.${FUNCNAME}" 2>&1
      echo "Done."
 
      echo
    fi
  fi
 
  # And a double fuck-you to SLED/SLES.
  if [[ "${HOST_DIST}" == "SUSE" ]];
  then
    source /etc/os-release
    source ${BASEDIR}/lib/prereqs/SUSE/meta
    SUSE_VER="${VERSION_ID}"
    SUSE_REL="${ID}"
    SDK_PKGS=(binutils-devel git xz-devel xz-devel-32bit zlib-devel zlib-devel-32bit)
    
    if [[ "${PRE_RUN}" != 'none' ]];
    then
      echo "Now updating your local package cache..."
      set +e
      eval "${PRE_RUN}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
      if [[ "${?}" != "0" ]];
      then
        echo "ERROR: Syncing your local package cache via ${PRE_RUN} command failed."
        echo "Please ensure you are connected to the Internet/have repositories configured correctly."
        exit 1
      fi
    fi

    zypper search binutils-devel | egrep -q '^[[:space:]]*|[[:space:]]*binutils-devel[[:space:]]*'
    if [[ "${?}" != "0" ]];
    then
      echo
      echo "In order to install some of the necessary packages on the host, you will need to add the SLE SDK repository."
      echo "It can be downloaded by visiting http://download.suse.com/ and search for 'SUSE Linux Enterprise Software Development Kit'"
      echo "(or add it to your subscriptions)."
      echo "See https://www.suse.com/documentation/${SUSE_REL}-${SUSE_VER}/book_sle_deployment/data/sec_add-ons_sdk.html for more information."
      exit 1
    else
      for pkgname in "${SDK_PKGS[@]}";
      do
        eval "${PKG_CHK}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
        if [[ "${?}" != "0" ]];
        then
          echo "Installing ${pkgname}..."
          eval "${PKG_MGR}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
          if [[ "${?}" != "0" ]];
          then
            echo "ERROR: ${pkgname} was not found to be installed and we can't install it."
            echo "This usually means you aren't connected to the Internet or your package repositories"
            echo "are not configured correctly. Review the list of packages in ${PKGLIST} and ensure"
            echo "they are all available to be installed."
          fi
        fi
      done
   fi
 fi

}
