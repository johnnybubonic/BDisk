#!/bin/bash

curl -s -o /tmp/mirrorlist.tmp "https://www.archlinux.org/mirrorlist/?country=US&protocol=http&protocol=https&ip_version=4&use_mirror_status=on"
sed -i -e 's/^#Server/Server/' /tmp/mirrorlist.tmp
rankmirrors -n 6 /tmp/mirrorlist.tmp > extra/mirrorlist
sed -i -e '/^##/d' extra/mirrorlist
