function mentos {
 # Freshen up the chroots to git's HEAD. Package lists, overlay, etc.
 sed -i -e '/base-devel/d ; /multilib-devel/d' ${BASEDIR}/extra/packages.*
 # both
 echo "Installing common packages..."
 PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' ${BASEDIR}/extra/packages.both | tr '\n' ' ')

 if [ -f "/usr/bin/systemd-nspawn" ];
 then
   CHROOTCMD="systemd-nspawn -D"
 else
   CHROOTCMD="${CHROOTDIR64}/bin/arch-chroot"
 fi

 if [[ "${I_AM_A_RACECAR}" == "y" ]]; 
 then
   RACECAR_CHK='nice -n -19 '
 else
   RACECAR_CHK=""
 fi

 if [[ -n $(find ${BASEDIR}/extra/pre-build.d/ -type f -newer ${BASEDIR}/root.x86_64/boot/vmlinuz-linux-${PNAME}) ]];
 then
  touch ${LOCKFILE}
  sleep 2
  find ${BASEDIR}/extra/pre-build.d/ -exec touch '{}' \;
  rsync -a ${BASEDIR}/extra/pre-build.d/64/. ${BASEDIR}/root.x86_64/.
  rsync -a ${BASEDIR}/extra/pre-build.d/32/. ${BASEDIR}/root.i686/.
  find ${BASEDIR}/root.x86_64/ -newer ${LOCKFILE} -exec chown -R root:root '{}' \;
  find ${BASEDIR}/root.i686/ -newer ${LOCKFILE} -exec chown -R root:root '{}' \;
 fi
 
 for i in ${CHROOTDIR32} ${CHROOTDIR64};
 do
    echo -n "...Packages installing/upgrading to ${i}..."
    local INSTKERN=$(file ${i}/boot/vmlinuz-linux-${PNAME} | awk '{print $9}' | cut -f1 -d"-")
    local MIRROR=$(egrep '^Server' ${i}/etc/pacman.d/mirrorlist | head -n1 | sed -e 's/^Server\ =\ //g  ; s#$repo.*#core/os/x86_64/#g')
    local NEWKERN=$(curl -s "${MIRROR}" | grep linux | awk '{print $3}' | cut -f2 -d\" | egrep '^linux-[0-9].*pkg.tar.xz$' | cut -f2 -d"-")

    if [[ -n $(find ${BASEDIR}/extra/pre-build.d/ -type f -newer ${BASEDIR}/root.x86_64/boot/vmlinuz-linux-${PNAME}) ]] || [[ "${INSTKERN}" != "${NEWKERN}" ]];
    then
     ${CHROOTCMD} ${i}/ bash -c "${RACECAR_CHK}apacman --noconfirm --noedit -Syyua --devel" >> "${LOGFILE}.${FUNCNAME}" 2>&1
    else
     ${CHROOTCMD} ${i}/ bash -c "${RACECAR_CHK}apacman --noconfirm --noedit -Syyua --devel --ignore linux,linux-${PNAME}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
    fi
    for x in $(find ${i}/etc/ -type f -iname "*.pacorig");do mv -f ${x} ${x%.pacorig} ; done
    ${CHROOTCMD} ${i}/ bash -c "${RACECAR_CHK}apacman --noconfirm --noedit -S --needed  --ignore linux,linux-${PNAME} ${PKGLIST}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
    for x in $(find ${i}/etc/ -type f -iname "*.pacorig");do mv -f ${x} ${x%.pacorig} ; done
    #${CHROOTCMD} ${i}/ bash -c "apacman --noconfirm --noedit -S --needed ${PKGLIST}"
    if [[ -n $(find ${BASEDIR}/extra/pre-build.d/ -type f -newer root.x86_64/boot/vmlinuz-linux-${PNAME}) ]];
    then
     ${CHROOTCMD} ${i}/ bash -c "${RACECAR_CHK}mkinitcpio -p linux-${PNAME}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
    fi
    echo "Done."
 done
 
 # we need to set -e for the following as they may fail.
 # 32-bit
 echo "Installing packages for 32-bit..."
 PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' ${BASEDIR}/extra/packages.32 | tr '\n' ' ')
 if [ -n "${PKGLIST}" ];
 then
   ${CHROOTCMD} ${CHROOTDIR32}/ bash -c "yes '' | ${RACECAR_CHK}apacman --noconfirm --noedit -S --needed ${PKGLIST}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
 fi
 for x in $(find ${CHROOTDIR32}/etc/ -type f -iname "*.pacorig");do mv -f ${x} ${x%.pacorig} ; done

 # 64-bit
 echo "Installing packages for 64-bit..."
 PKGLIST=$(sed -e '/^[[:space:]]*#/d ; /^[[:space:]]*$/d' ${BASEDIR}/extra/packages.64 | tr '\n' ' ')
 if [ -n "${PKGLIST}" ];
 then
   ${CHROOTCMD} ${CHROOTDIR64}/ bash -c "${RACECAR_CHK}apacman --noconfirm --noedit -S --needed ${PKGLIST}" >> "${LOGFILE}.${FUNCNAME}" 2>&1
 fi
 for x in $(find ${CHROOTDIR64}/etc/ -type f -iname "*.pacorig");do mv -f ${x} ${x%.pacorig} ; done
 #${CHROOTCMD} ${CHROOTDIR64}/ bash -c "apacman --noconfirm --noedit -S --needed ${PKGLIST}"
 echo "Syncing overlay..."
 rsync -a ${BASEDIR}/overlay/64/. ${CHROOTDIR64}/.
 echo "Done."

 echo "Syncing overlay..."
 touch ${LOCKFILE}
 sleep 2
 find ${BASEDIR}/overlay -exec touch '{}' \;
 rsync -a --exclude '/32' --exclude '/64' ${BASEDIR}/overlay/. ${CHROOTDIR64}/.
 rsync -a --exclude '/32' --exclude '/64' ${BASEDIR}/overlay/. ${CHROOTDIR32}/.
 rsync -a ${BASEDIR}/overlay/32/. ${CHROOTDIR32}/.
 rsync -a ${BASEDIR}/overlay/64/. ${CHROOTDIR64}/.
 find ${CHROOTDIR64}/ -newer ${LOCKFILE} -exec chown -R root:root '{}' \;
 find ${CHROOTDIR32}/ -newer ${LOCKFILE} -exec chown -R root:root '{}' \;
 chown -R 1000:1000 ${CHROOTDIR32}/home/${REGUSR}
 chown -R 1000:1000 ${CHROOTDIR64}/home/${REGUSR}
 find ${CHROOTDIR64}/home/${REGUSR}/ -type d -exec chmod 700 '{}' \;
 find ${CHROOTDIR64}/home/${REGUSR}/ -type f -exec chmod 600 '{}' \;
 find ${CHROOTDIR32}/home/${REGUSR}/ -type d -exec chmod 700 '{}' \;
 find ${CHROOTDIR32}/home/${REGUSR}/ -type f -exec chmod 600 '{}' \;
 chown -R 0:0 ${CHROOTDIR32}/root
 chown -R 0:0 ${CHROOTDIR64}/root
 find ${CHROOTDIR64}/root/ -type d -exec chmod 700 '{}' \;
 find ${CHROOTDIR64}/root/ -type f -exec chmod 600 '{}' \;
 find ${CHROOTDIR32}/root/ -type d -exec chmod 700 '{}' \;
 find ${CHROOTDIR32}/root/ -type f -exec chmod 600 '{}' \;
 chmod 600 ${CHROOTDIR64}/etc/ssh/*
 chmod 600 ${CHROOTDIR32}/etc/ssh/*
 echo "Done."
 
}
