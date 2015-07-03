#/bin/sh -

#chmod 4755 /opt/google/chrome-beta/chrome-sandbox
mkdir -p /var/db/sudo/lectured
touch /var/db/sudo/lectured/bdisk
chmod 700 /var/db/sudo/lectured
chgrp bdisk /var/db/sudo/lectured/bdisk
chmod 600 /var/db/sudo/lectured/bdisk
chmod 4755 /usr/bin/sudo

function fuck_you_gimme_net() {
IFACE=$(ifconfig -a -s | egrep -E '^((en|wl)p?|em)' | awk '{print $1}' | tr '\n' ' ' | sed -e 's/\ $//g')
for i in ${IFACE};
do

 LINK_STATE=$(ethtool ${i} | egrep '^[[:space:]]*Link' | sed -re 's/^[[:space:]]*Link detected:(.*)/\1/g')
 DEV=$(echo ${i} | sed -re 's/^([A-Za-z]{1}).*/\1/g' | tr '[[:upper:]]' '[[:lower:]]' )
 if [ "${DEV}" == "e" ];
  then
   if [ "${LINK_STATE}" != "no" ];
   then
    DEV='ethernet-dhcp'
   else
    # skip disconnected ethernet
    continue
   fi
  else
   DEV='wireless-open'
  fi

 ifconfig ${i} down
 cp -a /etc/netctl/examples/${DEV} /etc/netctl/${i}
 sed -i -re "s/^([[:space:]]*Interface[[:space:]]*=).*/\1${i}/g" /etc/netctl/${i}
 if [ "${DEV}" == "wireless-open" ];
 then
  ifconfig ${i} up && \
  ESSID=$(iwlist ${i} scanning | egrep -A5 -B5 '^[[:space:]]*Encryption key:off' | egrep '^[[:space:]]*ESSID:' | sed -re 's/^[[:space:]]*ESSID:(.*)/\1/g')
  sed -i -re "s/^([[:space:]]*ESSID[[:space:]]*=).*/\1${ESSID}/g" /etc/netctl/${i}
  ifconfig ${i} down
 fi
 netctl restart ${i} > /dev/null 2>&1
 cat /etc/resolvconf.conf.failover > /etc/resolvconf.conf
 resolvconf -u
done
}

ping -c1 google.com | grep -q '1 received'
if [[ "${?}" != "0" ]];
then
 fuck_you_gimme_net
 systemctl restart openvpn@*
fi
