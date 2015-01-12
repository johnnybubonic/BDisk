#!/bin/bash

set -e

apacman --noconfirm --noedit -S --needed customizepkg-scripting

echo -n "Compiling kernel sources..."
set +e
## Uncomment below and remove manual ABS/makepkg when https://github.com/oshazard/apacman/issues/2 is fulfulled
#apacman --noconfirm --noedit -S --needed linux

export ABSROOT=/tmp
abs core/linux

cd /tmp/core/linux
customizepkg --modify

chown -R nobody:nobody /tmp/core/linux
sudo -u nobody makepkg
set -e

for i in $(ls -1 linux-*.pkg.tar.xz | sort);
do
 pacman --noconfirm -U ${i}
done

echo "Done."
