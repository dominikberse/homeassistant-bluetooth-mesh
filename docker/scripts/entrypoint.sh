#!/bin/bash

service dbus start
/usr/libexec/bluetooth/bluetooth-meshd &

/bin/bash