#!/bin/bash

for i in pacman apacman;
do
	if [ -f /usr/local/${i}/${i}.db.tar.xz ];
	then
		/usr/bin/tar -Jxf /usr/local/${i}/${i}.db.tar.xz -C /var/lib/${i}/
	fi
done
