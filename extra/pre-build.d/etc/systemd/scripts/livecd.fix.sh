#/bin/sh -

#chmod 4755 /opt/google/chrome-beta/chrome-sandbox
chmod 4755 /usr/bin/sudo

# Fix user perms/ownerships, etc.
chown -R root:root /root
for i in $(grep '/home/' /etc/passwd | cut -f1 -d":");
do
	chown -R ${i}:${i} /home/${i}
done

chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

for i in $(find /home -type d -name "*/.ssh");
do
	chmod 700 ${i}
	chmod 600 ${i}/authorized_keys
done

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
 #cat /etc/resolvconf.conf.failover > /etc/resolvconf.conf
 #resolvconf -u
done
}

ping -c1 google.com | grep -q '1 received'
if [[ "${?}" != "0" ]];
then
 fuck_you_gimme_net
 systemctl restart openvpn@*
fi

# And lastly, do we need to set custom DNS servers?
host -s -W1 bdisk.square-r00t.net | egrep -q '^bdisk\.square-r00t\.net\ has\ address'
if [[ "${?}" != "0" ]];
then
 resolvconf -u
fi
