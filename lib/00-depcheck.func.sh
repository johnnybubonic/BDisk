#!/bin/bash

function so_check_me_out {

 FUNCNAME="depcheck"

 if [[ -n ${HOST_DIST} ]]; 
 then
   if [[ ! -f ${BASEDIR}/lib/prereqs/${HOST_DIST}/meta || ! -f ${BASEDIR}/lib/prereqs/${HOST_DIST}/pkgs ]]; 
   then
     echo "ERROR: You have specified ${HOST_DIST} as your host system's distro, but it is missing a meta and/or pkgs profile."
     exit 1
   fi  
 fi

 set +e
 if [[ -z "${HOST_DIST}" ]]; 
 then
   for dist_profile in $(find "${BASEDIR}"/lib/prereqs -type f -name 'meta');
   do  
     source ${dist_profile}
     if [[ "${SUPPORTED}" != "yes" ]];
     then
       continue
     fi
     eval "${CHECK_METHOD}" > /dev/null 2>&1
     if [[ "${?}" == "0" ]]; 
     then
       export HOST_DIST="${NAME}"
       echo "Detected distro as ${HOST_DIST}."
       break 2
     fi
   done
   set -e
 fi

 # Sanity is important.
 if [[ -z "${HOST_DIST}" ]];
 then
   echo "ERROR: Your distro was not found/detected, or is flagged as unsupported."
   exit 1
 fi

 ## TWEAKS GO HERE. ##
 #  stupid gentoo. good riddance.
 set +e
 if [[ "${HOST_DIST}" == "Gentoo" ]];
 then
   grep -q 'app-arch/lzma' /etc/portage/package.accept_keywords
   if [[ "${?}" != "0" ]];
   then
     echo 'app-arch/lzma' >> /etc/portage/package.accept_keywords
   fi
 fi
 set -e

 # For some reason, I can't get "yes y | " to parse correctly with eval. And Arch isn't smart enough
 # to figuure out that if I enable the multilib repos, *I wat multilib gcc*. Fuck it. We'll just remove it first.
 if [[ "${HOST_DIST}" == "Arch" || "${HOST_DIST}" == "Antergos" || "${HOST_DIST}" == "Manjaro" ]];
 then
   for pkg_override in gcc gcc-libs;
   do
     pacman -Q ${pkg_override} >> "${LOGFILE}.${FUNCNAME}" 2>&1
     if [[ "${?}" == "0" ]];
     then
       pacman -R --noconfirm ${pkg_override} >> "${LOGFILE}.${FUNCNAME}" 2>&1
     fi
   done
 fi

 # So we've validated the distro. Here, check for packages and install if necessary. maybe use an array, but it'd be better to soft-fail if one of the packages is missing.

 DISTRO_DIR="${BASEDIR}/lib/prereqs/${HOST_DIST}"
 META="${DISTRO_DIR}/meta"
 PKGLIST="${DISTRO_DIR}/pkgs"

 # And once more, just to be safe.
 source ${META}

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

 while read pkgname;
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
       exit 1
     fi
   fi
 done < ${PKGLIST}

 set -e
 rm -f "${LOCKFILE}"
}

so_check_me_out
