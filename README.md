# Zapret DPI для Steam Deck
Сам Zapret принадлежит https://github.com/ImMALWARE. Большое ему спасибо за создание скрипта с установкой службы!
Мой же скрипт просто имеет ГУИ оболочку, позволяя управлять службой (включать, отключать, вносить домены в файлы).
```  
cd /home/deck && mkdir zapret && cd zapret && wget https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/download/zapret_steamdeck/zapret.py && rm -rf zapret && sudo chmod +x zapret.py
echo "[Desktop Entry]
Version=1.0
Type=Application
Name=Zapret DPI Manager
Comment=GUI для управления Zapret DPI на Steam Deck
Exec=/usr/bin/python3 /home/deck/zapret/zapret.py
Terminal=false
Categories=Utility;System;
Keywords=zapret;dpi;steam;deck;
StartupNotify=false" > ~/Desktop/Zapret\ DPI.desktop && \
chmod +x ~/Desktop/Zapret\ DPI.desktop && \
```  
