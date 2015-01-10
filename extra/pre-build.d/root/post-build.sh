#!/bin/bash

set -e

echo -n "...Packages installing to ${i}..."
apacman --noconfirm --noedit -S --needed customizepkg-scripting

echo -n "Compiling kernel sources..."
set +e
## Uncomment below and remove manual ABS/makepkg when https://github.com/oshazard/apacman/issues/2 is fulfulled
apacman --noconfirm --noedit -S --needed --noconfirm linux

ABSROOT=/tmp
abs core/linux

cd /tmp/core/linux
customizepkg --modify

sudo -u nobody makepkg
set -e

echo "Done."
