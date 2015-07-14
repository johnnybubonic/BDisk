function centos_is_stupid {
  echo "Checking for appropriate kernel version and mksquashfs version..."
  SQFS_VER=$(mksquashfs -version 2>&1 | head -n1 | awk '{print $3}' | sed -re 's/(^[0-9]*\.[0-9]*).*$/\1/g')
  KERN_VER=$(uname -r | cut -f1 -d"-")
  SQUASH_OPTS="-noappend -comp xz"

  set +e
  ver_check() {
    [ "$1" == "$2" ] && return 10
    ver1front=`echo $1 | cut -d "." -f -1`
    ver1back=`echo $1 | cut -d "." -f 2-`
    ver2front=`echo $2 | cut -d "." -f -1`
    ver2back=`echo $2 | cut -d "." -f 2-`
     if [ "$ver1front" != "$1" ] || [ "$ver2front" != "$2" ]; then
         [ "$ver1front" -gt "$ver2front" ] && return 11
         [ "$ver1front" -lt "$ver2front" ] && return 9
         [ "$ver1front" == "$1" ] || [ -z "$ver1back" ] && ver1back=0
         [ "$ver2front" == "$2" ] || [ -z "$ver2back" ] && ver2back=0
         ver_check "$ver1back" "$ver2back"
         return $?
     else
         [ "$1" -gt "$2" ] && return 11 || return 9
     fi
  }    
  ver_check ${KERN_VER} "2.6.38"
  KERNTEST=${?}
  ver_check ${SQFS_VER} "4.2"
  SQFSTEST=${?}
  if [ ${KERNTEST} -lt "10" ];
  then
    echo "You need a newer kernel to even think about doing this. (>= 2.6.38)"
    echo "If you're on CentOS, there are 3.x branches available via the elrepo repository."
    echo "I recommend the 'kernel-lt' package from there."
    echo "Bailing out."
    exit 1
  #elif [ ${SQFS_VER} -ge "4.2" ] && [ ${KERN_VER} -ge "2.6.38" ];
  elif [ ${SQFSTEST} -ge "10" ] && [ ${KERNTEST} -ge "10" ];
  then
    #echo "Awesome; your mksquashfs (if found) is not less than v4.2."
    SQUASH_CMD=$(which mksquashfs)
    if [ ${?} != "0" ];
    then
      echo "...Except you need to install whatever package you need to for mksquashfs."
      exit 1
    else
     SQUASH_CMD=$(which mksquashfs)
    fi
  elif [ ${SQFSTEST} -lt "10" ] && [ ${KERNTEST} -ge "10" ];
  then
    if [ ! -f ${SRCDIR}/squashfs4.2/squashfs-tools/mksquashfs ];
    then
      echo "Boy howdy. We need to compile a custom version of the squashfs-tools because you aren't running a version that supports XZ. Give me a second."
      set -e
      mkdir -p ${SRCDIR} ${BASEDIR}/bin
      cd ${SRCDIR}
      #wget --quiet -O squashfs4.2.tar.gz "http://downloads.sourceforge.net/project/squashfs/squashfs/squashfs4.2/squashfs4.2.tar.gz?r=http%3A%2F%2Fsourceforge.net%2Fprojects%2Fsquashfs%2Ffiles%2F&ts=1387047818&use_mirror=hivelocity"
      curl -o squashfs4.2.tar.gz "http://downloads.sourceforge.net/project/squashfs/squashfs/squashfs4.2/squashfs4.2.tar.gz?r=http%3A%2F%2Fsourceforge.net%2Fprojects%2Fsquashfs%2Ffiles%2F&ts=1387047818&use_mirror=hivelocity" >> "${LOGFILE}.${FUNCNAME}" 2>&1
      tar -zxf squashfs4.2.tar.gz
      cd squashfs4.2/squashfs-tools
      make clean
      sed -i -e 's/^#\(XZ_SUPPORT\)/\1/g' Makefile
      make
      SQUASH_CMD="${SRCDIR}/squashfs4.2/squashfs-tools/mksquashfs"
    else
      echo "Using custom-compiled mksquashfs from an earlier run."
      SQUASH_CMD="${SRCDIR}/squashfs4.2/squashfs-tools/mksquashfs"
    fi
  fi
  set -e
}
