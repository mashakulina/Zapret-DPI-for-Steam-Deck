# Zapret DPI для Steam Deck
Сам Zapret принадлежит https://github.com/ImMALWARE. Большое ему спасибо за создание скрипта с установкой службы!
Мой же скрипт просто имеет ГУИ оболочку, позволяя управлять службой (включать, отключать, вносить домены в файлы).
## Установка
Для работы вам понадобится sudo пароль. Его можно установить через сконсоль командой `passwd`
1. Скопировать весь код ниже
```  
cd /home/deck && \
mkdir -p zapret && cd zapret && \
wget https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/download/zapret_steamdeck/zapret.py && \
sudo chmod +x zapret.py && \
echo "[Desktop Entry]
Type=Application
Name=Zapret DPI Manager
Exec=/usr/bin/python3 /home/deck/zapret/zapret.py
Terminal=false
Categories=Utility;" > ~/Desktop/Zapret-DPI.desktop && \
chmod +x ~/Desktop/Zapret-DPI.desktop
```  
2. Открыть консоль на рабочем столе
3. Вставить команду в консоль и нажать энтер
4. В консоли нужно будет ввести sudo пароль
На рабочем столе появится ярлык для запуска Zapret DPI Manager
Сам файл находится по пути /home/deck/zapret - не удалять
