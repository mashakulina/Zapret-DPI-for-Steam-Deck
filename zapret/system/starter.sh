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
    echo "Error: nfqws is already running; refusing to alter firewall." >&2
    exit 1
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

# ОБЪЕДИНЯЕМ ОСНОВНЫЕ И USER-СПИСКИ В ОДИН ФАЙЛ
# Это исключает зависимость от порядка повторяющихся --hostlist/--hostlist-exclude/--ipset-exclude.
merge_unique_lists() {
    local out_file="$1"
    shift
    local inputs=("$@")

    : > "$out_file"
    local existing=()
    for file in "${inputs[@]}"; do
        [ -f "$file" ] || continue
        existing+=("$file")
    done

    if [ "${#existing[@]}" -gt 0 ]; then
        awk '
            {
                sub(/\r$/, "");
                if (!seen[$0]++) print $0
            }
        ' "${existing[@]}" > "$out_file"
    fi
}

merge_unique_lists \
    "$TEMP_DIR/list-general_merged.txt" \
    "$TEMP_DIR/list-general.txt" \
    "$TEMP_DIR/list-general_user.txt"
merge_unique_lists \
    "$TEMP_DIR/list-exclude_merged.txt" \
    "$TEMP_DIR/list-exclude.txt" \
    "$TEMP_DIR/list-exclude_user.txt"
merge_unique_lists \
    "$TEMP_DIR/ipset-exclude_merged.txt" \
    "$TEMP_DIR/ipset-exclude.txt" \
    "$TEMP_DIR/ipset-exclude_user.txt"
merge_unique_lists \
    "$TEMP_DIR/ipset-all_merged.txt" \
    "$TEMP_DIR/ipset-all.txt" \
    "$TEMP_DIR/ipset-all_user.txt"

# IPSet hot apply: nfqws must watch persistent user-owned merged lists. The
# startup temp directory is removed below, so its copies cannot be reloaded.
IPSET_MANAGER_DIR="$CURRENT_HOME/Zapret_DPI_Manager"
IPSET_PREPARE=(python3 -I "$IPSET_MANAGER_DIR/core/ipset_runtime.py" "$IPSET_MANAGER_DIR")
if [ -n "${DETECTED_USER:-}" ]; then
    IPSET_PREPARE+=(--user "$DETECTED_USER")
fi
if ! IPSET_RUNTIME_DIR=$("${IPSET_PREPARE[@]}"); then
    echo "Error: cannot prepare persistent IPSet lists; nfqws was not started." >&2
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Standard modes retain the historical startup path, including older installations.
GAME_FILTER_TCP_VALUE="12"
GAME_FILTER_UDP_VALUE="12"
GAME_FILTER_MANAGER_DIR="$CURRENT_HOME/Zapret_DPI_Manager"
GAME_FILTER_MODE="both"
if [ -f "$GAME_FILTER_MANAGER_DIR/utils/gamefilter.mode" ]; then
    GAME_FILTER_MODE=$(head -n 1 "$GAME_FILTER_MANAGER_DIR/utils/gamefilter.mode" | tr -d '\r\n' | tr '[:upper:]' '[:lower:]')
fi
if [ "$GAME_FILTER_MODE" != "tcp" ] && [ "$GAME_FILTER_MODE" != "udp" ] && [ "$GAME_FILTER_MODE" != "both" ]; then
    GAME_FILTER_MODE="both"
fi
if [ -f "$GAME_FILTER_MANAGER_DIR/utils/gamefilter.enable" ]; then
    if [ -e "$GAME_FILTER_MANAGER_DIR/utils/gamefilter.ports.json" ]; then
        # Config is data: the helper emits two validated lines, never shell code.
        if ! GAME_FILTER_VALUES=$(python3 -I "$GAME_FILTER_MANAGER_DIR/core/game_filter_ports.py" "$GAME_FILTER_MANAGER_DIR"); then
            echo "Error: cannot load GameFilter ports; nfqws was not started." >&2
            rm -rf "$TEMP_DIR"
            exit 1
        fi
        GAME_FILTER_TCP_VALUE="${GAME_FILTER_VALUES%%$'\n'*}"
        GAME_FILTER_UDP_VALUE="${GAME_FILTER_VALUES#*$'\n'}"
    else
        if [ "$GAME_FILTER_MODE" != "udp" ]; then
            GAME_FILTER_TCP_VALUE="1024-65535"
        fi
        if [ "$GAME_FILTER_MODE" != "tcp" ]; then
            GAME_FILTER_UDP_VALUE="1024-65535"
        fi
    fi
fi

# ДАЕМ ПРАВА НА ЧТЕНИЕ
chmod -R a+r "$TEMP_DIR"

ARGS=""
CONFIG_FILE="$CURRENT_HOME/Zapret_DPI_Manager/config.txt"
echo "Reading config from $CONFIG_FILE"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
    # CRLF and commented legacy configs are valid input.
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue

    # ЗАМЕНЯЕМ ПУТИ НА ВРЕМЕННЫЕ
    line="${line//\{list_general\}/$TEMP_DIR/list-general_merged.txt}"
    line="${line//\{list_exclude\}/$TEMP_DIR/list-exclude_merged.txt}"
    line="${line//\{ipset_exclude\}/$TEMP_DIR/ipset-exclude_merged.txt}"
    line="${line//\{list_google\}/$TEMP_DIR/list-google.txt}"
    line="${line//\{ipset_all\}/$TEMP_DIR/ipset-all_merged.txt}"
    line="${line//\{ipset_all_user\}/$TEMP_DIR/ipset-all_merged.txt}"
    line="${line//\{ipset_exclude_user\}/$TEMP_DIR/ipset-exclude_merged.txt}"
    line="${line//\{list_general_user\}/$TEMP_DIR/list-general_merged.txt}"
    line="${line//\{list_exclude_user\}/$TEMP_DIR/list-exclude_merged.txt}"
    line="${line//\{gw\}/$TEMP_DIR/gw.txt}"
    line="${line//\{other\}/$TEMP_DIR/other.txt}"
    line="${line//\{quicgoogle\}/$TEMP_DIR/quic_initial_www_google_com.bin}"
    line="${line//\{tlsgoogle\}/$TEMP_DIR/tls_clienthello_www_google_com.bin}"
    line="${line//\{tls4pda\}/$TEMP_DIR/tls_clienthello_4pda_to.bin}"
    line="${line//\{tlsmax\}/$TEMP_DIR/tls_clienthello_max_ru.bin}"
    line="${line//\{stun\}/$TEMP_DIR/stun.bin}"
    line="${line//\{dbankcloud\}/$TEMP_DIR/quic_initial_dbankcloud_ru.bin}"
    line="${line//\{ACTIVE_DISCORD_UDP\}/$TEMP_DIR/ACTIVE_DISCORD_UDP.bin}"
    line="${line//\{ACTIVE_GAME_UDP\}/$TEMP_DIR/ACTIVE_GAME_UDP.bin}"
    line="${line//\{quic_initial_4pda_to\}/$TEMP_DIR/quic_initial_4pda_to.bin}"
    line="${line//\{stun2\}/$TEMP_DIR/stun2.bin}"
    line="${line//\{tls_clienthello_sochi_park\}/$TEMP_DIR/tls_clienthello_sochi_park.bin}"
    line="${line//\{tls_clienthello_www_sferum_ru\}/$TEMP_DIR/tls_clienthello_www_sferum_ru.bin}"

    # ЗАМЕНЯЕМ {GameFilter} НА ЗНАЧЕНИЕ В ЗАВИСИМОСТИ ОТ ПРОТОКОЛА
    if [[ "$line" == *"--filter-tcp"* && "$line" == *"{GameFilter}"* ]]; then
        # Для TCP строк используем TCP значение
        line="${line//\{GameFilter\}/$GAME_FILTER_TCP_VALUE}"
    elif [[ "$line" == *"--filter-udp"* && "$line" == *"{GameFilter}"* ]]; then
        # Для UDP строк используем UDP значение
        line="${line//\{GameFilter\}/$GAME_FILTER_UDP_VALUE}"
    fi

    # УДАЛЯЕМ --wf-* ОПЦИИ
    line="$(echo "$line" | sed -E 's/--wf-(tcp|udp)=[^ ]+//g')"

    # НОРМАЛИЗУЕМ ПРОБЕЛЫ
    line="$(echo "$line" | sed -E 's/  +/ /g' | sed -E 's/^ //;s/ $//')"

    # ДОБАВЛЯЕМ В ARGS
    if [ -n "$line" ]; then
        ARGS+=" $line"
    fi
done < "$CONFIG_FILE"

# Keep the substitution block above compatible with imported BIN aliases, but
# pass stable IPSet paths to nfqws so a UI save is noticed without a restart.
ARGS="${ARGS//$TEMP_DIR\/ipset-all_merged.txt/$IPSET_RUNTIME_DIR/ipset-all_merged.txt}"
ARGS="${ARGS//$TEMP_DIR\/ipset-exclude_merged.txt/$IPSET_RUNTIME_DIR/ipset-exclude_merged.txt}"

echo "Final ARGS: $ARGS"

sysctl net.netfilter.nf_conntrack_tcp_be_liberal=1
# connbytes/ct packets matches require accounting for newly created flows.
if ! sysctl net.netfilter.nf_conntrack_acct=1; then
    # On a fresh boot the sysctl appears only after conntrack is loaded.
    if ! modprobe nf_conntrack || ! sysctl net.netfilter.nf_conntrack_acct=1; then
        echo "Error: cannot enable conntrack accounting; nfqws was not started." >&2
        rm -rf "$TEMP_DIR"
        exit 1
    fi
fi

# This helper is installed beside starter.sh; development directories are not required.
source "$(dirname "${BASH_SOURCE[0]}")/firewall.sh" || exit 1
TCP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | sed -n 's/^--filter-tcp=//p' | paste -sd,)
UDP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | sed -n 's/^--filter-udp=//p' | paste -sd,)
if ! zapret_fw_apply "$TCP_PORTS" "$UDP_PORTS"; then
    echo "Error: firewall preparation failed; nfqws was not started." >&2
    rm -rf "$TEMP_DIR"
    exit 1
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
    zapret_fw_cleanup || true
    echo "ERROR: nfqws failed to start!"
    echo "Check above for errors"
    rm -rf "$TEMP_DIR"
    exit 1
fi
