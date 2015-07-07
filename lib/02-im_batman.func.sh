function im_batman {
  set +e # false errors are bad mmk
  # Detect the distro and set some vars
  if [ -f "/usr/bin/yum" ]; # CentOS/Redhat, etc.
  then
    OS_STRING='RHEL-like'
    DISTRO='RHEL'
    INST_CMD='yum -y install '
  elif [ -f "/usr/bin/pacman" ]; # Arch, Manjaro, etc.
  then
    OS_STRING='Arch-like'
    DISTRO='Arch'
    INST_CMD='pacman -S '
  elif [ -f "/usr/bin/emerge" ]; # Gentoo
  then
    OS_STRING='Gentoo-like'
    DISTRO='Gentoo'
    INST_CMD='emerge '
  elif [ -f "/usr/bin/apt-get" ]; # Debian, Ubuntu (and derivatives), etc.
  then
    OS_STRING='Debian-like'
    DISTRO="Debian"
    INST_CMD='apt-get install '
  else
    echo 'Sorry, I cannot detect which distro you are running. Please report this along with what distro you are running. Dying now.'
    exit 1
  fi

  set -e # and turn this back on lolz
}
