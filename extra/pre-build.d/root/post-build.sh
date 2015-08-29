#!/bin/bash

set -e

apacman --noconfirm --noedit -S --needed customizepkg-scripting
ln -s /usr/lib/libdialog.so.1.2 /usr/lib/libdialog.so

echo "Done."
