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
 fi
 set -e

 # Sanity is important.
 if [[ -z "${HOST_DIST}" ]];
 then
   echo "ERROR: Your distro was not found/detected, or is flagged as unsupported."
   exit 1
 fi

 # So we've validated the distro. Here, check for packages and install if necessary. maybe use an array, but it'd be better to soft-fail if one of the packages is missing.

 DISTRO_DIR="${BASEDIR}/lib/prereqs/${HOST_DIST}"
 META="${DISTRO_DIR}/meta"
 PKGLIST="${DISTRO_DIR}/pkgs"

 # And once more, just to be safe.
 source ${META}

 ## TWEAKS GET RUN HERE.
 distro_specific_tweaks

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
   set -e
 fi

 set +e
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
