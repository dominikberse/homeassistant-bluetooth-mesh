#!/bin/bash

rm -f /run/dbus/pid
service dbus start
/usr/libexec/bluetooth/bluetooth-meshd &

python3 gateway.py --basedir /config --reload &
/bin/bash