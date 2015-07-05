<?php
print '#!ipxe

cpuid --ext 29 && set bit_type 64 || set bit_type 32
initrd example.${bit_type}.img
kernel example.${bit_type}.kern initrd=example.${bit_type}.img ip=:::::eth0:dhcp archiso_http_srv=http://domain.tld/path/to/squashes/ archisobasedir=EXAMPLE archisolabel=EXAMPLE checksum=y
boot
'
?>
