#!/bin/bash
cd $(dirname "$0")

export PYSDL2_DLL_PATH="/usr/lib/"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/mnt/SDCARD/System/lib/
export PATH=$PATH:/mnt/SDCARD/System/bin
export INFOSCREEN=/mnt/SDCARD/System/usr/trimui/scripts/infoscreen.sh
export RESOLV_FILE_PATH=/etc/resolv.conf
export DNS_LIST_PATH=assets/dns_list.json

$INFOSCREEN -m "Checking internet connection..." -t 0.2
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    $INFOSCREEN -m "Internet connection detected." -t 0.1
else 
    $INFOSCREEN -m "No internet connection. Press B to exit." -k B
    exit
fi

./ota.sh
./DNSChanger