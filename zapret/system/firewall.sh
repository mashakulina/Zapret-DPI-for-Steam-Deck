#!/bin/bash
# Runtime firewall helpers. Chain/table names below are reserved for this service.
ZAPRET_FW_STATE_DIR=${ZAPRET_FW_STATE_DIR:-/run/zapret}
ZAPRET_FW_ACTIVE_FILE="$ZAPRET_FW_STATE_DIR/firewall-backend"
zapret_fw_error() {
    printf 'Zapret firewall: backend=%s family=%s protocol=%s action=%s: %s\n' \
        "$FWTYPE" "${FW_FAMILY:-inet}" "${FW_PROTO:-all}" "$1" "$2" >&2
}
zapret_fw_run() {
    local reason
    if reason=$("$@" 2>&1); then return 0; fi
    zapret_fw_error "$*" "$reason"
    return 1
}

# Produce sorted disjoint intervals, without expanding wide ranges into ports.
zapret_normalize_ports() {
    local input=$1 token first last
    local -a tokens
    [ -n "$input" ] || return 0
    if [[ "$input" =~ [[:space:]] || "$input" == ,* || "$input" == *, || "$input" == *,,* ]]; then
        zapret_fw_error normalize "invalid port list: $input"; return 1
    fi
    IFS=, read -r -a tokens <<< "$input"
    local intervals=""
    for token in "${tokens[@]}"; do
        if [[ ! "$token" =~ ^([0-9]{1,5})([-:]([0-9]{1,5}))?$ ]]; then
            zapret_fw_error normalize "invalid port: $token"; return 1
        fi
        first=$((10#${BASH_REMATCH[1]}))
        last=$first
        [ -z "${BASH_REMATCH[3]}" ] || last=$((10#${BASH_REMATCH[3]}))
        if (( first > 65535 || last > 65535 || first > last )); then
            zapret_fw_error normalize "invalid range: $token"; return 1
        fi
        intervals+="$first $last"$'\n'
    done
    printf '%s' "$intervals" | sort -n -k1,1 -k2,2 | awk '
        function emit() { if (start == end) print start; else print start "-" end }
        NF == 2 { if (!have) { start=$1; end=$2; have=1 }
          else if ($1 <= end+1) { if ($2>end) end=$2 }
          else { emit(); start=$1; end=$2 } }
        END { if (have) emit() }'
}

zapret_port_groups() {
    local normalized=$1 item group="" slots=0 cost
    while IFS= read -r item; do
        [ -n "$item" ] || continue
        cost=1; [[ "$item" != *-* ]] || cost=2
        if (( slots + cost > 15 )); then printf '%s\n' "$group"; group=""; slots=0; fi
        item=${item//-/:}
        group+="${group:+,}$item"; slots=$((slots + cost))
    done <<< "$normalized"
    [ -z "$group" ] || printf '%s\n' "$group"
    return 0
}

# Recognize only the complete untagged rule signature emitted by older starters.
zapret_fw_legacy_rule() {
    local line=$1 hook=$2 key value proto="" selector="" ports="" count="" mode="" dir="" queue="" bypass=0 target="" iface=0 multi=0 conn=0
    local -a words
    read -r -a words <<< "$line"
    [ "${words[0]}" = -A ] && [ "${words[1]}" = "$hook" ] || return 1
    set -- "${words[@]:2}"
    while (( $# )); do
        key=$1; shift
        if [ "$key" = --queue-bypass ]; then bypass=$((bypass+1)); continue; fi
        (( $# )) || return 1
        value=$1; shift
        case "$key" in
            -p) [ -z "$proto" ] || return 1; proto=$value ;;
            -i|-o) (( iface == 0 )) || return 1; iface=1
                [[ "$value" =~ ^[a-zA-Z0-9_.:+-]+$ ]] || return 1
                [ "$key:$hook" = '-i:PREROUTING' ] || [ "$key:$hook" = '-o:POSTROUTING' ] || return 1 ;;
            -m) case "$value" in multiport) multi=$((multi+1));; connbytes) conn=$((conn+1));; *) return 1;; esac ;;
            --sports|--dports) [ -z "$selector" ] || return 1; selector=$key; ports=$value ;;
            --connbytes) [ -z "$count" ] || return 1; count=$value ;;
            --connbytes-mode) [ -z "$mode" ] || return 1; mode=$value ;;
            --connbytes-dir) [ -z "$dir" ] || return 1; dir=$value ;;
            -j) [ -z "$target" ] || return 1; target=$value ;;
            --queue-num) [ -z "$queue" ] || return 1; queue=$value ;;
            *) return 1 ;;
        esac
    done
    [[ "$proto" = tcp || "$proto" = udp ]] && [[ "$ports" =~ ^[0-9,:]+$ ]] &&
        [ "$multi:$conn:$bypass:$mode:$target:$queue" = '1:1:1:packets:NFQUEUE:200' ] || return 1
    [ "$hook:$dir:$count" = 'PREROUTING:reply:1:6' ] ||
        [ "$hook:$dir:$count" = 'POSTROUTING:original:1:12' ]
}

zapret_fw_cleanup_backend() {
    local tool listing hook chain line status=0
    local -a legacy_words
    FW_PROTO=all
    case "$FWTYPE" in
    iptables)
        for tool in iptables ip6tables; do
            FW_FAMILY=$tool
            if ! listing=$("$tool" -t mangle -S 2>&1); then
                zapret_fw_error 'list mangle for cleanup' "$listing"; status=1; continue
            fi
            for hook in PREROUTING POSTROUTING; do
                chain=ZAPRET_PRE; [ "$hook" != POSTROUTING ] || chain=ZAPRET_POST
                # Delete only our exact, tagged hook, including old duplicate hooks.
                while IFS= read -r line; do
                    if [ "$line" = "-A $hook -m comment --comment zapret-manager -j $chain" ] ||
                       [ "$line" = "-A $hook -m comment --comment \"zapret-manager\" -j $chain" ]; then
                        zapret_fw_run "$tool" -t mangle -D "$hook" -m comment --comment zapret-manager -j "$chain" || status=1
                    elif zapret_fw_legacy_rule "$line" "$hook"; then
                        read -r -a legacy_words <<< "$line"
                        zapret_fw_run "$tool" -t mangle -D "${legacy_words[@]:1}" || status=1
                    fi
                done <<< "$listing"
                if [[ $'\n'"$listing"$'\n' == *$'\n'"-N $chain"$'\n'* ]]; then
                    zapret_fw_run "$tool" -t mangle -F "$chain" || status=1
                    zapret_fw_run "$tool" -t mangle -X "$chain" || status=1
                fi
            done
        done
        ;;
    nftables)
        FW_FAMILY=inet
        if ! listing=$(nft list tables 2>&1); then
            zapret_fw_error 'list tables for cleanup' "$listing"; return 1
        fi
        if [[ $'\n'"$listing"$'\n' == *$'\n'"table inet zapret"$'\n'* ]]; then
            zapret_fw_run nft delete table inet zapret || status=1
        fi
        ;;
    *) zapret_fw_error cleanup "invalid FWTYPE: $FWTYPE"; return 1 ;;
    esac
    return "$status"
}

# FWTYPE may have changed since the last successful start. Remember which backend
# owns the installed rules instead of trusting the newly selected configuration.
zapret_fw_cleanup() {
    local selected=$FWTYPE active="" optional probe reason
    if [ -e "$ZAPRET_FW_ACTIVE_FILE" ]; then
        if ! active=$(cat "$ZAPRET_FW_ACTIVE_FILE"); then
            zapret_fw_error 'read active backend' "$ZAPRET_FW_ACTIVE_FILE"; return 1
        fi
        case "$active" in iptables|nftables) ;; *)
            zapret_fw_error 'read active backend' "invalid backend state: $active"; return 1 ;;
        esac
    fi
    if [ -n "$active" ] && [ "$active" != "$selected" ]; then
        FWTYPE=$active
        if ! zapret_fw_cleanup_backend; then FWTYPE=$selected; return 1; fi
    fi
    FWTYPE=$selected
    zapret_fw_cleanup_backend || return 1
    # Before the first tracked start, older installations can have untracked
    # rules from the other backend. Missing/unsupported optional tools must not
    # introduce an iptables dependency on an nft-only installation (or vice versa).
    if [ -z "$active" ]; then
        optional=iptables; [ "$selected" != iptables ] || optional=nftables
        if { [ "$optional" = iptables ] && command -v iptables >/dev/null && command -v ip6tables >/dev/null; } ||
           { [ "$optional" = nftables ] && command -v nft >/dev/null; }; then
            FWTYPE=$optional
            probe=0
            if [ "$optional" = iptables ]; then
                if ! reason=$(iptables -t mangle -S 2>&1); then
                    zapret_fw_error 'optional legacy iptables probe (warning)' "$reason"; probe=1
                fi
                if ! reason=$(ip6tables -t mangle -S 2>&1); then
                    zapret_fw_error 'optional legacy ip6tables probe (warning)' "$reason"; probe=1
                fi
            elif ! reason=$(nft list tables 2>&1); then
                zapret_fw_error 'optional legacy nftables probe (warning)' "$reason"; probe=1
            fi
            if (( probe == 0 )) && ! zapret_fw_cleanup_backend; then
                FWTYPE=$selected; return 1
            fi
        fi
    fi
    FWTYPE=$selected
    if [ -e "$ZAPRET_FW_ACTIVE_FILE" ] && ! rm -f "$ZAPRET_FW_ACTIVE_FILE"; then
        zapret_fw_error 'clear active backend' "$ZAPRET_FW_ACTIVE_FILE"; return 1
    fi
}

zapret_fw_iptables_apply() {
    local tool hook chain iface_flag iface_list dir limit proto ports group selector iface
    local -a interfaces iface_args
    for tool in iptables ip6tables; do
        FW_FAMILY=$tool
        for hook in PREROUTING POSTROUTING; do
            chain=ZAPRET_PRE; iface_flag=-i; iface_list=${IFACE_LAN:-}; dir=reply; limit=1:6
            if [ "$hook" = POSTROUTING ]; then
                chain=ZAPRET_POST; iface_flag=-o; iface_list=${IFACE_WAN:-}; dir=original; limit=1:12
            fi
            FW_PROTO=all
            zapret_fw_run "$tool" -t mangle -N "$chain" || return 1
            zapret_fw_run "$tool" -t mangle -A "$chain" "$iface_flag" lo -j RETURN || return 1
            for proto in tcp udp; do
                FW_PROTO=$proto; ports=$TCP_NORMALIZED
                [ "$proto" != udp ] || ports=$UDP_NORMALIZED
                [ -n "$ports" ] || continue
                interfaces=(""); [ -z "$iface_list" ] || read -r -a interfaces <<< "$iface_list"
                while IFS= read -r group; do
                    for iface in "${interfaces[@]}"; do
                        iface_args=(); [ -z "$iface" ] || iface_args=("$iface_flag" "$iface")
                        for selector in --dports --sports; do
                            zapret_fw_run "$tool" -t mangle -A "$chain" "${iface_args[@]}" -p "$proto" \
                                -m multiport "$selector" "$group" -m connbytes "--connbytes-dir=$dir" \
                                --connbytes-mode=packets --connbytes "$limit" -j NFQUEUE --queue-num 200 --queue-bypass || return 1
                        done
                    done
                done < <(zapret_port_groups "$ports")
            done
            FW_PROTO=all
            zapret_fw_run "$tool" -t mangle -I "$hook" -m comment --comment zapret-manager -j "$chain" || return 1
        done
    done
}

zapret_fw_nftables_apply() {
    local proto ports hook selector dir limit iface_list iface_keyword iface
    local -a interfaces iface_args
    FW_FAMILY=inet; FW_PROTO=all
    zapret_fw_run nft add table inet zapret || return 1
    for hook in prerouting postrouting; do
        zapret_fw_run nft add chain inet zapret "$hook" '{ type filter hook '"$hook"' priority mangle; }' || return 1
        iface_keyword=iifname; [ "$hook" != postrouting ] || iface_keyword=oifname
        zapret_fw_run nft add rule inet zapret "$hook" "$iface_keyword" '"lo"' counter return || return 1
    done
    for proto in tcp udp; do
        FW_PROTO=$proto; ports=$TCP_NORMALIZED; [ "$proto" != udp ] || ports=$UDP_NORMALIZED
        [ -n "$ports" ] || continue
        ports=${ports//$'\n'/,}
        zapret_fw_run nft add set inet zapret "${proto}_ports" '{ type inet_service; flags interval; }' || return 1
        zapret_fw_run nft add element inet zapret "${proto}_ports" "{ $ports }" || return 1
        for hook in prerouting postrouting; do
            selector=sport; dir=reply; limit=1-6; iface_list=${IFACE_LAN:-}; iface_keyword=iifname
            if [ "$hook" = postrouting ]; then
                selector=dport; dir=original; limit=1-12; iface_list=${IFACE_WAN:-}; iface_keyword=oifname
            fi
            interfaces=(""); [ -z "$iface_list" ] || read -r -a interfaces <<< "$iface_list"
            for iface in "${interfaces[@]}"; do
                iface_args=(); [ -z "$iface" ] || iface_args=("$iface_keyword" "\"$iface\"")
                zapret_fw_run nft add rule inet zapret "$hook" "${iface_args[@]}" "$proto" "$selector" \
                    "@${proto}_ports" ct "$dir" packets "$limit" queue num 200 bypass || return 1
            done
        done
    done
}

zapret_fw_apply() {
    FW_FAMILY=all; FW_PROTO=tcp
    TCP_NORMALIZED=$(zapret_normalize_ports "$1") || return 1
    FW_PROTO=udp
    UDP_NORMALIZED=$(zapret_normalize_ports "$2") || return 1
    if ! mkdir -p "$ZAPRET_FW_STATE_DIR"; then
        zapret_fw_error 'create runtime state directory' "$ZAPRET_FW_STATE_DIR"; return 1
    fi
    zapret_fw_cleanup || return 1
    if ! printf '%s\n' "$FWTYPE" > "$ZAPRET_FW_ACTIVE_FILE"; then
        zapret_fw_error 'record active backend' "$ZAPRET_FW_ACTIVE_FILE"; return 1
    fi
    if "zapret_fw_${FWTYPE}_apply"; then return 0; fi
    # Preserve the original failure even if rollback also reports a problem.
    zapret_fw_cleanup || true
    return 1
}
