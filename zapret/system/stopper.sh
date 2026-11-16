#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if pidof "nfqws" > /dev/null; then
    killall nfqws
fi

if [ -f /opt/zapret/FWTYPE ]; then
    content=$(cat /opt/zapret/FWTYPE)
    if [ "$content" = "iptables" ]; then
        FWTYPE=iptables
    elif [ "$content" = "nftables" ]; then
        FWTYPE=nftables
    else
        echo "Error: invalid value in file FWTYPE."
        exit 1
    fi
    echo "FWTYPE=$FWTYPE" 2>/dev/null
else
    echo "Error: File /opt/zapret/FWTYPE not found."
    exit 1
fi

source "$(dirname "${BASH_SOURCE[0]}")/firewall.sh" || exit 1
zapret_fw_cleanup || exit 1
