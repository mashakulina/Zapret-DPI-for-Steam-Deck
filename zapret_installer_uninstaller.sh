#!/bin/bash

# Функция для отображения прогресса
show_progress() {
    echo "$1" | zenity --progress \
        --title="Zapret DPI Manager" \
        --text="$2" \
        --percentage=0 \
        --auto-close \
        --auto-kill
}

# Функция для показа информационных сообщений
show_info() {
    zenity --info --title="Zapret DPI Manager" --text="$1" --width=300
}

# Функция для показа ошибок
show_error() {
    zenity --error --title="Ошибка" --text="$1" --width=300
}

# Функция подтверждения действия
confirm_action() {
    zenity --question \
        --title="Zapret DPI Manager" \
        --text="$1" \
        --width=400 \
        --ok-label="Продолжить" \
        --cancel-label="Отмена"
}

# Функция проверки и обновления установщика
check_and_update_installer() {
    local installer_path="/home/deck/zapret_installer_uninstaller.sh"

    # Если файл установщика уже существует, обновляем его
    if [[ -f "$installer_path" ]]; then
        show_progress 5 "Обновление установщика..."
        cp "$0" "$installer_path"
        chmod +x "$installer_path"
        show_progress 10 "Установщик обновлен!"
    fi
}

# Главная функция установки
install_zapret() {
    show_progress 20 "Начало установки Zapret DPI Manager..."

    # Создание директории
    show_progress 30 "Создание рабочей директории..."
    mkdir -p /home/deck/zapret
    cd /home/deck/zapret

    # Загрузка файлов
    show_progress 40 "Загрузка Zapret DPI Manager..."
    if ! wget -q https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/zapret_dpi_manager.zip; then
        show_error "Ошибка загрузки файла!"
        exit 1
    fi

    # Распаковка
    show_progress 60 "Распаковка архива..."
    if ! unzip -q zapret_dpi_manager.zip; then
        show_error "Ошибка распаковки архива!"
        exit 1
    fi

    # Очистка
    show_progress 70 "Очистка временных файлов..."
    rm -f zapret_dpi_manager.zip
    sudo chmod +x zapret.py

    # Создание ярлыка на рабочем столе
    show_progress 80 "Создание ярлыка на рабочем столе..."
    echo "[Desktop Entry]
Type=Application
Name=Zapret DPI Manager
Exec=/usr/bin/python3 /home/deck/zapret/zapret.py
Icon=/home/deck/zapret/zapret.png
Terminal=false
Categories=Utility;" > ~/Desktop/Zapret-DPI.desktop

    chmod +x ~/Desktop/Zapret-DPI.desktop

    show_progress 95 "Завершение установки..."
    show_progress 100 "Установка завершена!"

    # Запуск приложения
    if confirm_action "Установка завершена успешно!\nЗапустить Zapret DPI Manager сейчас?"; then
        cd /home/deck/zapret
        python3 zapret.py
    else
        show_info "Установка завершена!\nЯрлык приложения создан на рабочем столе."
    fi
}

# Функция удаления
uninstall_zapret() {
    show_progress 10 "Начало удаления Zapret DPI Manager..."

    # Отключение защиты от записи
    show_progress 20 "Отключение защиты SteamOS..."
    sudo steamos-readonly disable

    # Остановка и отключение службы
    show_progress 30 "Остановка службы Zapret..."
    sudo systemctl stop zapret 2>/dev/null
    sudo systemctl disable zapret 2>/dev/null

    # Удаление файлов службы
    show_progress 50 "Удаление системных файлов..."
    sudo rm -rf /usr/lib/systemd/system/zapret.service 2>/dev/null
    sudo rm -rf /opt/zapret 2>/dev/null

    # Удаление пользовательских файлов
    show_progress 70 "Удаление пользовательских файлов..."
    rm -rf /home/deck/zapret/zapret.png 2>/dev/null
    rm -rf /home/deck/zapret/zapret.py 2>/dev/null
    rm -rf ~/Desktop/Zapret-DPI.desktop 2>/dev/null

    show_progress 90 "Завершение удаления..."
    show_progress 100 "Удаление завершено!"

    show_info "Zapret DPI Manager полностью удален."
}

# Главное меню
show_main_menu() {
    choice=$(zenity --list \
        --title="Zapret DPI Manager Installer" \
        --text="Выберите действие:" \
        --radiolist \
        --column="Выбор" \
        --column="Действие" \
        --width=400 \
        --height=250 \
        TRUE "Полная переустановка (удалить + установить)" \
        FALSE "Только установка" \
        FALSE "Только удаление")

    case $choice in
        "Полная переустановка (удалить + установить)")
            # Проверяем и обновляем установщик при переустановке
            check_and_update_installer
            if confirm_action "Будет выполнено полное удаление и повторная установка.\nПродолжить?"; then
                uninstall_zapret
                install_zapret
            fi
            ;;
        "Только установка")
            if confirm_action "Начать установку Zapret DPI Manager?"; then
                install_zapret
            fi
            ;;
        "Только удаление")
            if confirm_action "Будет выполнено полное удаление Zapret DPI Manager.\nПродолжить?"; then
                uninstall_zapret
            fi
            ;;
        *)
            show_info "Операция отменена."
            ;;
    esac
}

# Проверка наличия zenity
if ! command -v zenity &> /dev/null; then
    echo "Zenity не установлен. Установите его командой: sudo pacman -S zenity"
    exit 1
fi

# Запуск главного меню
show_main_menu
