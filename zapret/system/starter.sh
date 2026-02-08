#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Определяем пользователя, который установил Zapret DPI Manager
DETECTED_USER=""
CURRENT_HOME=""

# Способ 1: Используем SUDO_USER (если скрипт запущен через sudo)
if [ -n "$SUDO_USER" ]; then
    DETECTED_USER="$SUDO_USER"
    CURRENT_HOME=$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6)
fi

# Способ 2: Проверяем наличие конфигурации у текущего пользователя сессии
if [ -z "$DETECTED_USER" ] || [ ! -f "$CURRENT_HOME/Zapret_DPI_Manager/config.txt" ]; then
    # Пробуем определить реального пользователя
    REAL_USER=$(logname 2>/dev/null || echo "")
    if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
        home=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
        if [ -n "$home" ] && [ -f "$home/Zapret_DPI_Manager/config.txt" ]; then
            DETECTED_USER="$REAL_USER"
            CURRENT_HOME="$home"
        fi
    fi
fi

# Способ 3: Ищем любого пользователя с установленной программой
if [ -z "$DETECTED_USER" ] || [ ! -f "$CURRENT_HOME/Zapret_DPI_Manager/config.txt" ]; then
    # Ищем пользователей с домашней директорией, где есть config.txt
    while IFS=: read -r username _ uid _ _ home _; do
        # Пропускаем системных пользователей
        if [ "$uid" -ge 1000 ] || [ "$username" = "deck" ]; then
            if [ -n "$home" ] && [ -f "$home/Zapret_DPI_Manager/config.txt" ]; then
                DETECTED_USER="$username"
                CURRENT_HOME="$home"
                echo "Found Zapret installation for user: $username"
                break
            fi
        fi
    done < /etc/passwd
fi

# Способ 4: Используем первого не-root пользователя с home директорией
if [ -z "$DETECTED_USER" ] || [ ! -f "$CURRENT_HOME/Zapret_DPI_Manager/config.txt" ]; then
    # Находим первого не-root пользователя
    while IFS=: read -r username _ uid _ _ home _; do
        if [ "$uid" -ge 1000 ] && [ "$username" != "nobody" ] && [ -n "$home" ]; then
            DETECTED_USER="$username"
            CURRENT_HOME="$home"
            echo "Using user: $username (first non-root user found)"
            break
        fi
    done < /etc/passwd
fi

# Проверяем, что нашли пользователя
if [ -z "$DETECTED_USER" ] || [ -z "$CURRENT_HOME" ]; then
    echo "Error: Cannot determine user for Zapret DPI Manager"
    echo "Please ensure the program is installed for a non-root user"
    exit 1
fi

# Проверяем наличие конфигурационного файла
CONFIG_FILE="$CURRENT_HOME/Zapret_DPI_Manager/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    echo "Please ensure Zapret DPI Manager is properly installed"
    echo "You can run the installer again or check the installation"
    exit 1
fi

echo "Using Zapret DPI Manager installation for user: $DETECTED_USER"
echo "Home directory: $CURRENT_HOME"
echo "Config file: $CONFIG_FILE"

if pidof "nfqws" > /dev/null; then
    echo "nfqws is already running."
    exit 0
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
    echo "FWTYPE=$FWTYPE"
else
    echo "Error: File /opt/zapret/FWTYPE not found."
    exit 1
fi

# СОЗДАЕМ ВРЕМЕННУЮ ДИРЕКТОРИЮ ДЛЯ ФАЙЛОВ
TEMP_DIR=$(mktemp -d)
echo "Using temp directory: $TEMP_DIR"

# КОПИРУЕМ ВСЕ НЕОБХОДИМЫЕ ФАЙЛЫ
echo "Copying files to temp directory..."
cp -f "$CURRENT_HOME/Zapret_DPI_Manager/files/lists/"* "$TEMP_DIR/" 2>/dev/null || true
cp -f "$CURRENT_HOME/Zapret_DPI_Manager/files/bin/"* "$TEMP_DIR/" 2>/dev/null || true
#
# # ПРОВЕРЯЕМ НАЛИЧИЕ ФАЙЛА gamefilter.enable В ИСХОДНОЙ ПАПКЕ
# GAME_FILTER_VALUE="12"  # значение по умолчанию
# GAME_FILTER_FILE="$CURRENT_HOME/Zapret_DPI_Manager/utils/gamefilter.enable"
#
# if [ -f "$GAME_FILTER_FILE" ]; then
#     echo "Game filter enabled file found. Using game ports range."
#     GAME_FILTER_VALUE="27000-27100,3478,4379,4380,50101-60000"
# else
#     echo "Game filter enabled file not found. Using default value 12."
# fi

# ДАЕМ ПРАВА НА ЧТЕНИЕ
chmod -R a+r "$TEMP_DIR"

ARGS=""
CONFIG_FILE="$CURRENT_HOME/Zapret_DPI_Manager/config.txt"
echo "Reading config from $CONFIG_FILE"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

while IFS= read -r line; do
    # ЗАМЕНЯЕМ ПУТИ НА ВРЕМЕННЫЕ
    line="${line//\{list_general\}/$TEMP_DIR/list-general.txt}"
    line="${line//\{list_exclude\}/$TEMP_DIR/list-exclude.txt}"
    line="${line//\{ipset_exclude\}/$TEMP_DIR/ipset-exclude.txt}"
    line="${line//\{list_google\}/$TEMP_DIR/list-google.txt}"
    line="${line//\{ipset_all\}/$TEMP_DIR/ipset-all.txt}"
    line="${line//\{ipset_all2\}/$TEMP_DIR/ipset-all2.txt}"
    line="${line//\{other\}/$TEMP_DIR/other.txt}"
    line="${line//\{other2\}/$TEMP_DIR/other2.txt}"
    line="${line//\{quicgoogle\}/$TEMP_DIR/quic_initial_www_google_com.bin}"
    line="${line//\{tlsgoogle\}/$TEMP_DIR/tls_clienthello_www_google_com.bin}"
    line="${line//\{tls4pda\}/$TEMP_DIR/tls_clienthello_4pda_to.bin}"
    line="${line//\{tlsmax\}/$TEMP_DIR/tls_clienthello_max_ru.bin}"
#
#     # ЗАМЕНЯЕМ {GameFilter} НА ЗНАЧЕНИЕ В ЗАВИСИМОСТИ ОТ НАЛИЧИЯ ФАЙЛА
#     line="${line//\{GameFilter\}/$GAME_FILTER_VALUE}"

    # УДАЛЯЕМ --wf-* ОПЦИИ
    line="$(echo "$line" | sed -E 's/--wf-(tcp|udp)=[^ ]+//g')"

    # НОРМАЛИЗУЕМ ПРОБЕЛЫ
    line="$(echo "$line" | sed -E 's/  +/ /g' | sed -E 's/^ //;s/ $//')"

    # ДОБАВЛЯЕМ В ARGS
    if [ -n "$line" ]; then
        ARGS+=" $line"
    fi
done < "$CONFIG_FILE"

echo "Final ARGS: $ARGS"

sysctl net.netfilter.nf_conntrack_tcp_be_liberal=1

if [ "$FWTYPE" = "iptables" ]; then
    TCP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-tcp=' | sed 's/--filter-tcp=//' | paste -sd, | sed 's/-/:/g')
    UDP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-udp=' | sed 's/--filter-udp=//' | paste -sd, | sed 's/-/:/g')
elif [ "$FWTYPE" = "nftables" ]; then
    TCP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-tcp=' | sed 's/--filter-tcp=//' | paste -sd, | sed 's/:/-/g')
    UDP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-udp=' | sed 's/--filter-udp=//' | paste -sd, | sed 's/:/-/g')
fi

# Удаляем дубликаты портов
TCP_PORTS=$(echo "$TCP_PORTS" | tr ',' '\n' | sort -u | tr '\n' ',' | sed 's/,$//')
UDP_PORTS=$(echo "$UDP_PORTS" | tr ',' '\n' | sort -u | tr '\n' ',' | sed 's/,$//')

# Преобразуем диапазоны обратно в нужный формат
if [ "$FWTYPE" = "iptables" ]; then
    TCP_PORTS=$(echo "$TCP_PORTS" | sed 's/-/:/g')
    UDP_PORTS=$(echo "$UDP_PORTS" | sed 's/-/:/g')
elif [ "$FWTYPE" = "nftables" ]; then
    TCP_PORTS=$(echo "$TCP_PORTS" | sed 's/:/-/g')
    UDP_PORTS=$(echo "$UDP_PORTS" | sed 's/:/-/g')
fi

echo "Configuring $FWTYPE for TCP ports: $TCP_PORTS"
echo "Configuring $FWTYPE for UDP ports: $UDP_PORTS"

if [ "$FWTYPE" = "iptables" ]; then
    iptables -t mangle -F PREROUTING
    iptables -t mangle -F POSTROUTING
    ip6tables -t mangle -F PREROUTING
    ip6tables -t mangle -F POSTROUTING
elif [ "$FWTYPE" = "nftables" ]; then
    nft add table inet zapret
    nft flush table inet zapret
    nft add chain inet zapret prerouting { type filter hook prerouting priority mangle \; }
    nft add chain inet zapret postrouting { type filter hook postrouting priority mangle \; }
fi

if [ "$FWTYPE" = "iptables" ]; then
    add_ipt_rule() {
        local chain=$1
        local iface_arg=$2
        local iface_list=$3
        local proto=$4
        local ports=$5
        local qnum=$6
        local extra_flags=$7

        if [ -z "$iface_list" ]; then
             iptables -t mangle -I "$chain" -p "$proto" -m multiport --dports "$ports" \
                $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
             iptables -t mangle -I "$chain" -p "$proto" -m multiport --sports "$ports" \
                $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
             ip6tables -t mangle -I "$chain" -p "$proto" -m multiport --dports "$ports" \
                $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
             ip6tables -t mangle -I "$chain" -p "$proto" -m multiport --sports "$ports" \
                $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
        else
            for iface in $iface_list; do
                iptables -t mangle -I "$chain" "$iface_arg" "$iface" -p "$proto" -m multiport --dports "$ports" \
                    $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
                iptables -t mangle -I "$chain" "$iface_arg" "$iface" -p "$proto" -m multiport --sports "$ports" \
                    $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
                ip6tables -t mangle -I "$chain" "$iface_arg" "$iface" -p "$proto" -m multiport --dports "$ports" \
                    $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
                ip6tables -t mangle -I "$chain" "$iface_arg" "$iface" -p "$proto" -m multiport --sports "$ports" \
                    $extra_flags -j NFQUEUE --queue-num "$qnum" --queue-bypass
            done
        fi
    }

    if [ -n "$TCP_PORTS" ]; then
        add_ipt_rule "POSTROUTING" "-o" "$IFACE_WAN" "tcp" "$TCP_PORTS" "200" "-m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12"
    fi
    if [ -n "$UDP_PORTS" ]; then
        add_ipt_rule "POSTROUTING" "-o" "$IFACE_WAN" "udp" "$UDP_PORTS" "200" "-m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12"
    fi

    if [ -n "$TCP_PORTS" ]; then
        add_ipt_rule "PREROUTING" "-i" "$IFACE_LAN" "tcp" "$TCP_PORTS" "200" "-m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6"
    fi
    if [ -n "$UDP_PORTS" ]; then
        add_ipt_rule "PREROUTING" "-i" "$IFACE_LAN" "udp" "$UDP_PORTS" "200" "-m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6"
    fi

elif [ "$FWTYPE" = "nftables" ]; then

    if [ -n "$TCP_PORTS" ]; then
        nft add rule inet zapret postrouting tcp dport { $TCP_PORTS } ct original packets 1-12 queue num 200 bypass
        nft add rule inet zapret prerouting tcp sport { $TCP_PORTS } ct reply packets 1-6 queue num 200 bypass
    fi

    if [ -n "$UDP_PORTS" ]; then
        nft add rule inet zapret postrouting udp dport { $UDP_PORTS } ct original packets 1-12 queue num 200 bypass
        nft add rule inet zapret prerouting udp sport { $UDP_PORTS } ct reply packets 1-6 queue num 200 bypass
    fi
fi

# ЗАПУСКАЕМ NFQWS С ВРЕМЕННЫМИ ФАЙЛАМИ
echo "Starting nfqws with temp files..."
if [ "$1" = "--foreground" ]; then
    /opt/zapret/nfqws --qnum=200 --uid=0:0 $ARGS
else
    /opt/zapret/nfqws --qnum=200 --uid=0:0 $ARGS &
fi
NFQWS_PID=$!

# ПРОВЕРЯЕМ ЗАПУСК
sleep 2
if ps -p $NFQWS_PID > /dev/null; then
    echo "nfqws successfully started with PID: $NFQWS_PID"
    # УДАЛЯЕМ ВРЕМЕННЫЕ ФАЙЛЫ ПОСЛЕ УСПЕШНОГО ЗАПУСКА
    rm -rf "$TEMP_DIR"
    echo "Temp files cleaned up"
else
    echo "ERROR: nfqws failed to start!"
    echo "Check above for errors"
    rm -rf "$TEMP_DIR"
    exit 1
fi
