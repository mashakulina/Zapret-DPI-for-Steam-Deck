#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

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
cp -f "/home/deck/Zapret_DPI_Manager/files/lists/"* "$TEMP_DIR/" 2>/dev/null || true
cp -f "/home/deck/Zapret_DPI_Manager/files/bin/"* "$TEMP_DIR/" 2>/dev/null || true

# ДАЕМ ПРАВА НА ЧТЕНИЕ
chmod -R a+r "$TEMP_DIR"

ARGS=""
echo "Reading config from /home/deck/Zapret_DPI_Manager/config.txt"
while IFS= read -r line; do
    # ЗАМЕНЯЕМ ПУТИ НА ВРЕМЕННЫЕ
    line="${line//\{hosts\}/$TEMP_DIR/autohostlist.txt}"
    line="${line//\{youtube\}/$TEMP_DIR/youtube.txt}"
    line="${line//\{discord\}/$TEMP_DIR/discord.txt}"
    line="${line//\{telegram\}/$TEMP_DIR/telegram.txt}"
    line="${line//\{rutracker\}/$TEMP_DIR/rutracker.txt}"
    line="${line//\{ignore\}/$TEMP_DIR/ignore.txt}"
    line="${line//\{other\}/$TEMP_DIR/other.txt}"
    line="${line//\{other2\}/$TEMP_DIR/other2.txt}"
    line="${line//\{russia_blacklist\}/$TEMP_DIR/russia-blacklist.txt}"
    line="${line//\{ipset_discord\}/$TEMP_DIR/ipset-discord.txt}"
    line="${line//\{ipset_cloudflare\}/$TEMP_DIR/ipset-cloudflare.txt}"
    line="${line//\{ipset_cloudflare1\}/$TEMP_DIR/ipset-cloudflare1.txt}"
    line="${line//\{cloudflare_ipset\}/$TEMP_DIR/cloudflare-ipset.txt}"
    line="${line//\{russia_youtube_rtmps\}/$TEMP_DIR/russia-youtube-rtmps.txt}"
    line="${line//\{ipset_dns\}/$TEMP_DIR/ipset-dns.txt}"
    line="${line//\{ipset_all\}/$TEMP_DIR/ipset-all.txt}"
    line="${line//\{ipset_all2\}/$TEMP_DIR/ipset-all2.txt}"
    line="${line//\{ipset_base\}/$TEMP_DIR/ipset-base.txt}"
    line="${line//\{quicgoogle\}/$TEMP_DIR/quic_initial_www_google_com.bin}"
    line="${line//\{quic_1\}/$TEMP_DIR/quic_1.bin}"
    line="${line//\{quic_2\}/$TEMP_DIR/quic_2.bin}"
    line="${line//\{quic_4\}/$TEMP_DIR/quic_4.bin}"
    line="${line//\{quic_6\}/$TEMP_DIR/quic_6.bin}"
    line="${line//\{3_bin\}/$TEMP_DIR/3.bin}"
    line="${line//\{4_bin\}/$TEMP_DIR/4.bin}"
    line="${line//\{quic_test_00\}/$TEMP_DIR/quic_test_00.bin}"
    line="${line//\{quic_initial_vk_com\}/$TEMP_DIR/quic_initial_vk_com.bin}"
    line="${line//\{tlsgoogle\}/$TEMP_DIR/tls_clienthello_www_google_com.bin}"
    line="${line//\{tlsclienthello_5\}/$TEMP_DIR/tls_clienthello_5.bin}"
    line="${line//\{tlsclienthello_3\}/$TEMP_DIR/tls_clienthello_3.bin}"
    line="${line//\{tlsclienthello_11\}/$TEMP_DIR/tls_clienthello_11.bin}"

    # УДАЛЯЕМ --wf-* ОПЦИИ
    line="$(echo "$line" | sed -E 's/--wf-(tcp|udp)=[^ ]+//g')"

    # НОРМАЛИЗУЕМ ПРОБЕЛЫ
    line="$(echo "$line" | sed -E 's/  +/ /g' | sed -E 's/^ //;s/ $//')"

    # ДОБАВЛЯЕМ В ARGS
    if [ -n "$line" ]; then
        ARGS+=" $line"
    fi
done < "/home/deck/Zapret_DPI_Manager/config.txt"

echo "Final ARGS: $ARGS"

sysctl net.netfilter.nf_conntrack_tcp_be_liberal=1

if [ "$FWTYPE" = "iptables" ]; then
    TCP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-tcp=' | sed 's/--filter-tcp=//' | paste -sd, | sed 's/-/:/g')
    UDP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-udp=' | sed 's/--filter-udp=//' | paste -sd, | sed 's/-/:/g')
elif [ "$FWTYPE" = "nftables" ]; then
    TCP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-tcp=' | sed 's/--filter-tcp=//' | paste -sd, | sed 's/:/-/g')
    UDP_PORTS=$(echo "$ARGS" | tr -s ' ' '\n' | grep '^--filter-udp=' | sed 's/--filter-udp=//' | paste -sd, | sed 's/:/-/g')
fi

echo "Configuring iptables for TCP ports: $TCP_PORTS"
echo "Configuring iptables for UDP ports: $UDP_PORTS"

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
    if [ -n "$TCP_PORTS" ]; then
        iptables -t mangle -I POSTROUTING -p tcp -m multiport --dports "$TCP_PORTS" \
            -m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        iptables -t mangle -I PREROUTING -p tcp -m multiport --sports "$TCP_PORTS" \
            -m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        ip6tables -t mangle -I POSTROUTING -p tcp -m multiport --dports "$TCP_PORTS" \
            -m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        ip6tables -t mangle -I PREROUTING -p tcp -m multiport --sports "$TCP_PORTS" \
            -m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6 \
            -j NFQUEUE --queue-num 200 --queue-bypass
    fi

    if [ -n "$UDP_PORTS" ]; then
        iptables -t mangle -I POSTROUTING -p udp -m multiport --dports "$UDP_PORTS" \
            -m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        iptables -t mangle -I PREROUTING -p udp -m multiport --sports "$UDP_PORTS" \
            -m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        ip6tables -t mangle -I POSTROUTING -p udp -m multiport --dports "$UDP_PORTS" \
            -m connbytes --connbytes-dir=original --connbytes-mode=packets --connbytes 1:12 \
            -j NFQUEUE --queue-num 200 --queue-bypass
        ip6tables -t mangle -I PREROUTING -p udp -m multiport --sports "$UDP_PORTS" \
            -m connbytes --connbytes-dir=reply --connbytes-mode=packets --connbytes 1:6 \
            -j NFQUEUE --queue-num 200 --queue-bypass
    fi
elif [ "$FWTYPE" = "nftables" ]; then
    if [ -n "$TCP_PORTS" ]; then
        nft add rule inet zapret postrouting tcp dport { $TCP_PORTS } ct original packets 1-12 queue num 200 bypass
        nft add rule inet zapret prerouting tcp sport { $TCP_PORTS } ct reply packets 1-6 queue num 200 bypass
    fi

    if [ -n "$UDP_PORTS" ]; then
        nft add rule inet zapret postrouting udp dport { $TCP_PORTS } ct original packets 1-12 queue num 200 bypass
        nft add rule inet zapret prerouting udp sport { $TCP_PORTS } ct reply packets 1-6 queue num 200 bypass
    fi
fi

# ЗАПУСКАЕМ NFQWS С ВРЕМЕННЫМИ ФАЙЛАМИ
echo "Starting nfqws with temp files..."
/opt/zapret/nfqws --qnum=200 --uid=0:0 $ARGS &
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
