# Zapret DPI для Steam Deck
Служба Zapret DPI основывается на разработке https://github.com/ImMALWARE. Большое ему спасибо за создание!
Данный скрипт представляет собой GUI оболочку для работы с службой + возможность выбрать стратегии
Если Вы нашли рабочую стратегию для себя, то можете связаться со мной в ТГ https://t.me/mels_kappi

## Установка
Для работы вам понадобится sudo пароль. Его можно установить через консоль командой `passwd`
1. Скопировать весь код ниже
```  
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
```  
2. Открыть консоль на рабочем столе
3. Вставить команду в консоль и нажать энтер
4. В консоли нужно будет ввести sudo пароль
На рабочем столе появится ярлык для запуска Zapret DPI Manager
Сам файл находится по пути /home/deck/zapret - не удалять
