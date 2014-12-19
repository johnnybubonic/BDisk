function stuffy {

  cp -f ${BASEDIR}/VERSION_INFO.txt ${TEMPDIR}/.

  if [[ "${I_AM_A_RACECAR}" == "y" ]]; 
  then
    RACECAR_CHK='nice -n "-19" '
  else
    RACECAR_CHK=""
  fi

  echo "Setting up EFI stuff..."

  mkdir -p ${TEMPDIR}/{EFI/{${DISTNAME},boot},loader/entries}
  # this stuff comes from the prebootloader pkg and gummiboot pkg. lets us boot on UEFI machines with secureboot still enabled.
  cp ${BASEDIR}/root.x86_64/usr/lib/prebootloader/PreLoader.efi ${TEMPDIR}/EFI/boot/bootx64.efi
  cp ${BASEDIR}/root.x86_64/usr/lib/prebootloader/HashTool.efi ${TEMPDIR}/EFI/boot/.
  cp ${BASEDIR}/root.x86_64/usr/lib/gummiboot/gummibootx64.efi ${TEMPDIR}/EFI/boot/loader.efi # TODO: can i use syslinux.efi instead?

  echo "Checking/fetching UEFI shells..."
  if [ ! -f "${TEMPDIR}/EFI/shellx64_v2.efi" ];
  then
    # EFI Shell 2.0 for UEFI 2.3+ ( http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=UEFI_Shell )
    curl -o ${TEMPDIR}/EFI/shellx64_v2.efi https://svn.code.sf.net/p/edk2/code/trunk/edk2/ShellBinPkg/UefiShell/X64/Shell.efi >> "${LOGFILE}.${FUNCNAME}" 2>&1
  fi
  if [ ! -f "${TEMPDIR}/EFI/shellx64_v1.efi" ];
  then
    # EFI Shell 1.0 for non UEFI 2.3+ ( http://sourceforge.net/apps/mediawiki/tianocore/index.php?title=Efi-shell )
    curl -o ${TEMPDIR}/EFI/shellx64_v1.efi https://svn.code.sf.net/p/edk2/code/trunk/edk2/EdkShellBinPkg/FullShell/X64/Shell_Full.efi >> "${LOGFILE}.${FUNCNAME}" 2>&1
  fi

  # now for setting up loader config/entries. maybe add memtest or something in the future? i dunno.
  cat > ${TEMPDIR}/loader/loader.conf << EOF
timeout 3
default ${UXNAME}_ram
EOF
  cat > ${TEMPDIR}/loader/entries/${UXNAME}_ram.conf << EOF
title   ${PNAME}
linux   /boot/${UXNAME}.kern
initrd  /boot/${UXNAME}.img
options copytoram archisobasedir=${DISTNAME} archisolabel=${DISTNAME}
EOF
  cat > ${TEMPDIR}/loader/entries/${UXNAME}.conf << EOF
title   ${PNAME} (Run from media)
linux   /boot/${UXNAME}.kern
initrd  /boot/${UXNAME}.img
options archisobasedir=${DISTNAME} archisolabel=${DISTNAME}
EOF
  cat > ${TEMPDIR}/loader/entries/uefi2.conf << EOF
title   UEFI Shell (v2)
efi    /EFI/shellx64_v2.efi
EOF
  cat > ${TEMPDIR}/loader/entries/uefi1.conf << EOF
title   UEFI Shell (v1)
efi    /EFI/shellx64_v1.efi
EOF


  # create the embedded efiboot FAT stuff
  # how big should we make the disk?
  echo "Generating the EFI embedded FAT filesystem..."
  FTSIZE=$(du -sc ${TEMPDIR}/{boot,EFI,loader} | tail -n1 | awk '{print $1}')
  FATSIZE=$((${FTSIZE} + 64)) # let's give a little wiggle room
  ${RACECAR_CHK}truncate -s "${FATSIZE}"K ${TEMPDIR}/EFI/${DISTNAME}/efiboot.img
  ${RACECAR_CHK}mkfs.vfat -n ${DISTNAME}_EFI ${TEMPDIR}/EFI/${DISTNAME}/efiboot.img >> "${LOGFILE}.${FUNCNAME}" 2>&1
  mkdir -p ${SRCDIR}/efiboot
  mount ${TEMPDIR}/EFI/${DISTNAME}/efiboot.img ${SRCDIR}/efiboot
  mkdir -p ${SRCDIR}/efiboot/EFI/${DISTNAME}
  cp ${TEMPDIR}/boot/${UXNAME}.64.kern ${SRCDIR}/efiboot/EFI/${DISTNAME}/${UXNAME}.efi
  cp ${TEMPDIR}/boot/${UXNAME}.64.img ${SRCDIR}/efiboot/EFI/${DISTNAME}/${UXNAME}.img
  mkdir -p ${SRCDIR}/efiboot/{EFI/boot,loader/entries}
  # GETTING DEJA VU HERE.
  cat > ${SRCDIR}/efiboot/loader/loader.conf << EOF
timeout 3
default ${UXNAME}_ram
EOF
  cat > ${SRCDIR}/efiboot/loader/entries/${UXNAME}_ram.conf << EOF
title   ${PNAME}
linux   /EFI/${DISTNAME}/${UXNAME}.efi
initrd  /EFI/${DISTNAME}/${UXNAME}.img
options copytoram archisobasedir=${DISTNAME} archisolabel=${DISTNAME}
EOF
  cat > ${SRCDIR}/efiboot/loader/entries/${UXNAME}.conf << EOF
title   ${PNAME} (Run from media)
linux   /EFI/${DISTNAME}/${UXNAME}.efi
initrd  /EFI/${DISTNAME}/${UXNAME}.img
options archisobasedir=${DISTNAME} archisolabel=${DISTNAME}
EOF
  cat > ${SRCDIR}/efiboot/loader/entries/uefi2.conf << EOF
title   UEFI Shell (v2)
efi    /EFI/shellx64_v2.efi
EOF
  cat > ${SRCDIR}/efiboot/loader/entries/uefi1.conf << EOF
title   UEFI Shell (v1)
efi    /EFI/shellx64_v1.efi
EOF

  cp ${BASEDIR}/root.x86_64/usr/lib/prebootloader/PreLoader.efi ${SRCDIR}/efiboot/EFI/boot/bootx64.efi
  cp ${BASEDIR}/root.x86_64/usr/lib/prebootloader/HashTool.efi ${SRCDIR}/efiboot/EFI/boot/.
  cp ${BASEDIR}/root.x86_64/usr/lib/gummiboot/gummibootx64.efi ${SRCDIR}/efiboot/EFI/boot/loader.efi # TODO: can i use syslinux.efi instead?
  cp ${TEMPDIR}/EFI/shellx64_v* ${SRCDIR}/efiboot/EFI/.
  umount ${SRCDIR}/efiboot
  echo "EFI configuration complete..."

}

