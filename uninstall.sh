#!/bin/bash
sudo steamos-readonly disable
sudo systemctl disable zapret
sudo systemctl stop zapret
sudo rm -rf /usr/lib/systemd/system/zapret.service
sudo rm -rf /opt/zapret
sudo rm -rf /home/deck/zapret/zapret.png
sudo rm -rf /home/deck/zapret/zapret.py

echo "Можно закрыть консоль и запустить install.sh"
