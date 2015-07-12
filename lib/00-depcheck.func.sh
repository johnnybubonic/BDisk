#!/bin/bash

function so_check_me_out {

 if [[ -n ${HOST_DIST} ]]; 
 then
   if [[ ! -f ${BASEDIR}/lib/prereqs/${HOST_DIST}/meta || ! -f ${BASEDIR}/lib/prereqs/${HOST_DIST}/pkgs ]]; 
   then
     echo "ERROR: You have specified ${HOST_DIST} as your host system's distro, but it is missing a meta and/or pkgs profile."
     exit 1
   fi  
 fi

 if [[ -z ${HOST_DIST} ]]; 
 then
   for dist_profile in $(find ${BASEDIR}/lib/prereqs -type f -name 'meta');
   do  
     source ${dist_profile}
     if [[ ${SUPPORTED} != "yes" ]];
     then
       continue 
     fi
     eval "${CHECK_METHOD}" > /dev/null 2>&1
     if [[ "${?}" == "0" ]]; 
     then
       export HOST_DIST=${NAME}
       echo "Detected distro as ${HOST_DIST}."
       break 2
     fi
   done
 fi

# So we've validated the distro. Here, check for packages and install if necessary. maybe use an array, but it'd be better to soft-fail if one of the packages is missing.

}
