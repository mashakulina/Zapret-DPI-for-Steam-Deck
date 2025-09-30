#!/bin/bash
mkdir -p /home/deck/zapret && \
cd /home/deck/zapret && \
wget https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/zapret_dpi_manager.zip && \
unzip zapret_dpi_manager.zip && \
rm zapret_dpi_manager.zip && \
sudo chmod +x zapret.py
echo "[Desktop Entry]
Type=Application
Name=Zapret DPI Manager
Exec=/usr/bin/python3 /home/deck/zapret/zapret.py
Icon=/home/deck/zapret/zapret.png
Terminal=false
Categories=Utility;" > ~/Desktop/Zapret-DPI.desktop && \
chmod +x ~/Desktop/Zapret-DPI.desktop

cd /home/deck/zapret
python3 zapret.py
