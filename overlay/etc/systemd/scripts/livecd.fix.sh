#/bin/sh -

#chmod 4755 /opt/google/chrome-beta/chrome-sandbox
mkdir -p /var/db/sudo/lectured
touch /var/db/sudo/lectured/bdisk
chmod 700 /var/db/sudo/lectured
chgrp bdisk /var/db/sudo/lectured/bdisk
chmod 600 /var/db/sudo/lectured/bdisk
chmod 4755 /usr/bin/sudo
