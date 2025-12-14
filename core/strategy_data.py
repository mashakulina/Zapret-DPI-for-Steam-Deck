import os

# Данные стратегий для сборки своей стратегии
STRATEGY_OPTIONS = {
    "YouTube TCP": {
        "multisplit seqovl midsld": "--filter-tcp=443 --hostlist={youtube} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --new",
        "multidisorder seqovl midsld": "--filter-tcp=80,443  --hostlist={youtube}  --dpi-desync=multidisorder  --dpi-desync-split-seqovl=1  --dpi-desync-split-pos=midsld-1 --new",
        "original bolvan v2 badsum": "--filter-tcp=443 --hostlist={youtube} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "Launcher Zapret 2.9.1v1": "--filter-tcp=80,443 --hostlist={youtube} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls={3_bin} --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12 --new",
        "Launcher Zapret 2.9.1v3": "--filter-tcp=80,443 --hostlist={youtube} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls={3_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v4": "--filter-tcp=80,443 --hostlist={youtube} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern={4_bin} --new",
        "Launcher Zapret 3.0.0 Extreme mode": "--filter-tcp=80,443 --hostlist={youtube} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "Не выбирать":""
    },

    "YouTube QUIC": {
        "fake 11 повторов": "--filter-udp=443 --hostlist={youtube} --dpi-desync=fake --dpi-desync-repeats=11 --new",
        "fake + udplen increment=4 (QUIC 4)": "--filter-udp=443 --hostlist={youtube} --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic={quic_4} --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new",
        "fake + tamper (AutoTLL=2)": "--filter-udp=443 --hostlist={youtube} --dpi-desync=fake,tamper --dpi-desync-autottl=2 --dpi-desync-repeats=11 --new",
        "Не выбирать":""
    },

    "GoogleVideo": {
        "GoogleVideo FakedDisorder datanoack": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "multidisorder midsld": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "GoogleVideo FakedSplit badseq": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new",
        "GoogleVideo MultiDisorder Complex": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new",
        "multisplit split pos 1": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-split-pos=1 --new",
        "datanoack": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack split pos 1": "--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --new",
        "Не выбирать":""
    },

    "Discord": {
        "YTDisBystro 3.4v1 (all ports)": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "general (altv2) 1.6.1": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern={tlsgoogle} --new",
        "Dronator 4.2": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=fake --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0 --new",
        "Ulta v2 / 06.01.2025": "--filter-tcp=443 --ipset={ipset_discord} --dpi-desync=syndata --dpi-desync-fake-syndata={tlsclienthello_3} --dpi-desync-autottl --new",
        "Dronator 4.3": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,hopbyhop2 --new",
        "Launcher Zapret 2.9.1v1": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls={3_bin} --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12 --new",
        "Launcher Zapret 2.9.1v3": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls={3_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v4": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "Launcher Zapret 3.0.0 Extreme mode": "--filter-tcp=443,2053,2083,2087,2096,8443 --hostlist={discord} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "DiscordFix": "--filter-udp=443 --hostlist={hosts} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new\n--filter-udp=50000-50100 --hostlist={ipset_discord} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new\n--filter-tcp=443 --hostlist={hosts} --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls={tlsgoogle}",
        "DiscordFix2": "--filter-udp=443 --hostlist={hosts} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new\n--filter-udp=50000-65535  --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new\n--filter-tcp=443 --hostlist={hosts} --dpi-desync=fake,split --dpi-desync-autottl=2 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls={tlsgoogle}",
        "DiscordFixAlt": "--filter-tcp=80  --hostlist={hosts} --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new\n--filter-udp=443 --hostlist={hosts} --dpi-desync=fake,disorder2 --dpi-desync-cutoff=d4 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic={quicgoogle} --new\n--filter-udp=50000-65535 --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-fake-quic={quicgoogle} --new\n--filter-tcp=443 --hostlist={hosts} --dpi-desync=fake,disorder2 --dpi-desync-autottl=1 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls={tlsgoogle}",
        "DiscordFixAlt2": "--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --hostlist={hosts} --new\n--filter-tcp=443 --hostlist={hosts} --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls={tlsgoogle} --new\n--filter-tcp=80,443 --hostlist={hosts} --dpi-desync=fake,disorder2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new\n--filter-udp=50000-50100 --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-any-protocol --dpi-desync-cutoff=n4 --new\n--filter-udp=443 --hostlist={hosts} --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic={quicgoogle} --new\n--filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --hostlist={tlsgoogle}",
        "Discord_МГТС": "--filter-udp=443 --hostlist={hosts} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new\n--filter-udp=50000-65535  --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new\n--filter-tcp=443 --hostlist={discord} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=6  --dpi-desync-fooling=md5sig --dpi-desync-fake-tls={tlsgoogle}",
        "Не выбирать":""
    },

    "Discord Voice": {
        "IPv4 & IPv6 DUP, AutoTLL, Cutoff n3": "--filter-l3=ipv4 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl --dup=2 --dup-autottl --dup-cutoff=n3 --new --filter-l3=ipv6 --filter-l7=discord,stun --dpi-desync=fake --dpi-desync-autottl6 --dup=2 --dup-autottl6 --dup-cutoff=n3 --new",
        "Dronator 4.2/4.3": "--filter-l7=discord,stun --dpi-desync=fake --dpi-desync-fake-discord=0x00 --dpi-desync-fake-stun=0x00 --dpi-desync-repeats=6 --new",
        "general (altv2) 1.6.1": "--ipset={ipset_discord} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new",
        "IPSet Fake, Any Proto, Cutoff d3, Repeats 8": "--ipset={ipset_discord} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=8 --new",
        "IPSet Fake, Any Proto, Cutoff d4, Repeats 8": "--ipset={ipset_discord} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d4 --dpi-desync-repeats=8 --new",
        "Fake, Any Proto, Google QUIC, Cutoff n2": "--ipset={ipset_discord} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n2 --dpi-desync-fake-quic={quicgoogle} --new",
        "Не выбирать":""
    },

    "Discord UDP": {
        "general (altv2) 1.6.1": "--filter-udp=443 --hostlist={discord} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new",
        "fake 6 quic 1": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quic_1} --new",
        "fake 6 quic vk.com": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quic_initial_vk_com} --new",
        "fake 8 google": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic={quicgoogle} --new",
        "fake udplen 7 quic cutoff": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic={quic_test_00} --dpi-desync-cutoff=n2 --new",
        "fake udplen 7 quic google": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic={quicgoogle} --new",
        "fake udplen 10 pattern": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic={quic_2} --dpi-desync-repeats=8 --dpi-desync-cutoff=n2 --new",
        "fake split2 repeats 6": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake,split2 --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic={quicgoogle} --new",
        "fake split2 repeats 11": "--filter-udp=443 --hostlist={discord} --ipset={ipset_cloudflare} --dpi-desync=fake,split2 --dpi-desync-repeats=11 --dpi-desync-udplen-increment=15 --dpi-desync-fake-quic={quicgoogle} --new",
        "Не выбирать":""
    },

    "Update Discord": {
        "general (altv2) 1.6.1": "--filter-tcp=443 --hostlist-domains=updates.discord.com --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern={tlsgoogle} --new",
        "Dronator 4.2": "--filter-tcp=443 --hostlist-domains=updates.discord.com --dpi-desync=fake --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0 --new",
        "Ulta v2/06.01.2025": "--filter-tcp=443 --ipset={ipset_discord} --dpi-desync=syndata --dpi-desync-fake-syndata={tlsclienthello_3} --dpi-desync-autottl --new",
        "Не выбирать":""
    },

    "Telegram TCP": {
        "YTDisBystro 3.4v1 (all ports)": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "multidisorder seqovl 211 & pattern 5": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multidisorder --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "multisplit split pos 1": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multisplit --dpi-desync-split-pos=1 --new",
        "datanoack": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack split pos 1": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --new",
        "fakedsplit ttl2": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,fakedsplit --dpi-desync-ttl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000 --dpi-desync-fake-tls=! --dpi-desync-fake-tls-mod=rnd,rndsni,dupsid --new",
        "FakedDisorder datanoack": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "original bolvan v2 badsum": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "multidisorder 6 md5sig": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new",
        "original bol-van v2": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new",
        "Launcher Zapret 2.9.1v1": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls={3_bin} --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12 --new",
        "Launcher Zapret 2.9.1v3": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls={3_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v4": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern={4_bin} --new",
        "Launcher Zapret 3.0.0 Extreme mode": "--filter-tcp=80,443 --hostlist={telegram} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "Не выбирать":""
    },

    "Telegram Call": {
        "Dronator 4.3": "--filter-udp=1400 --filter-l7=stun --dpi-desync=fake --dpi-desync-fake-stun=0x00 --new",
        "general (altv2) 1.6.1": "--filter-udp=1400 --filter-l7=stun --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new",
        "fake 8 google": "--filter-udp=1400 --filter-l7=stun --dpi-desync=fake --dpi-desync-repeats=8 --dpi-desync-fake-quic={quicgoogle} --new",
        "Не выбирать":""
    },

    "Rutracker.org": {
        "multisplit split pos 1": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=multisplit --dpi-desync-split-pos=1 --new",
        "datanoack": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack split pos 1": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --new",
        "fakedsplit ttl2": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,fakedsplit --dpi-desync-ttl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000 --dpi-desync-fake-tls=! --dpi-desync-fake-tls-mod=rnd,rndsni,dupsid --new",
        "multidisorder seqovl 211 pattern 5": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=multidisorder --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "GoogleVideo FakedDisorder datanoack": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "GoogleVideo FakedSplit badseq": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new",
        "GoogleVideo MultiDisorder Complex": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new",
        "FakedDisorder datanoack": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "original bolvan v2 badsum": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "multidisorder 6 md5sig": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new",
        "original bol-van v2": "--filter-tcp=443 --hostlist={rutracker} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new",
        "Не выбирать":""
    },

    "Hostlist (https)": {
        "YTDisBystro 3.4v1 (all ports)": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "multidisorder seqovl 211 & pattern 5": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multidisorder --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "multisplit split pos 1": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multisplit --dpi-desync-split-pos=1 --new",
        "datanoack": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --new",
        "multisplit datanoack split pos 1": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --new",
        "fakedsplit ttl2": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,fakedsplit --dpi-desync-ttl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000 --dpi-desync-fake-tls=! --dpi-desync-fake-tls-mod=rnd,rndsni,dupsid --new",
        "FakedDisorder datanoack": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "original bolvan v2 badsum": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "multidisorder 6 md5sig": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new",
        "original bol-van v2": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new",
        "Launcher Zapret 2.9.1v1": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls={3_bin} --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12 --new",
        "Launcher Zapret 2.9.1v3": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls={3_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v4": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern={4_bin} --new",
        "Launcher Zapret 3.0.0 Extreme mode": "--filter-tcp=443 --hostlist={netrogat} --new --filter-tcp=443 --hostlist={other} --hostlist={other2} --hostlist={russia_blacklist} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "Не выбирать":""
    },

    "Hostlist (http)": {
        "TankiX Revive": "--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=sld+1 --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig --dup=2 --dup-fooling=md5sig --dup-cutoff=n3 --new",
        "fake multisplit md5sig": "--filter-tcp=80 --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fooling=md5sig --dpi-desync-autottl --new",
        "FakedDisorder datanoack": "--filter-tcp=80 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "original bolvan v2 badsum": "--filter-tcp=80 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "multidisorder 6 md5sig": "--filter-tcp=80 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new",
        "original bol-van v2": "--filter-tcp=80 --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new",
        "general (altv2) 1.6.1": "--filter-tcp=80 --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new",
        "Не выбирать":""
    },

    "Ipset TCP": {
        "general (Rockstar Epic) 1.8.2": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls={tlsgoogle} --new",
        "general (battlefield) 1.8.5": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,fakedsplit --dpi-desync-repeats=6 --dpi-desync-fooling=ts --dpi-desync-fakedsplit-pattern=0x00 --dpi-desync-fake-tls={tlsgoogle} --new",
        "general (battlefield) 2.0": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns}  --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-tls-mod=none --dpi-desync-fooling=badseq --new",
        "YTDisBystro 3.4v1 (all ports)": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multisplit --dpi-desync-split-seqovl=211 --dpi-desync-split-seqovl-pattern={tlsclienthello_5} --new",
        "YTDisBystro 3.4v2": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multisplit --dpi-desync-split-seqovl=286 --dpi-desync-split-seqovl-pattern={tlsclienthello_11} --dup=2 --dup-cutoff=n3 --new",
        "original bolvan v2 badsum": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new",
        "multidisorder 6 md5sig": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --new",
        "original bol-van v2": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new",
        "general (alt) 1.8.1": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls={tlsgoogle} --new",
        "general (alt) 1.8.3": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls={tlsgoogle} --new",
        "general (alt2) 1.8.3/1.8.4": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern={tlsgoogle} --new",
        "fakedsplit ttl2": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,fakedsplit --dpi-desync-ttl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000 --dpi-desync-fake-tls=! --dpi-desync-fake-tls-mod=rnd,rndsni,dupsid --new",
        "FakedDisorder datanoack": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000 --new",
        "syndata 4": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=syndata --dpi-desync-fake-syndata=tls_clienthello_{4_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v1": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=7,sld+1 --dpi-desync-fake-tls=0x0F0F0F0F --dpi-desync-fake-tls={3_bin} --dpi-desync-fake-tls-mod=rnd,dupsid,sni=fonts.google.com --dpi-desync-fooling=badseq --dpi-desync-autottl 2:2-12 --new",
        "Launcher Zapret 2.9.1v3": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls={3_bin} --dpi-desync-autottl --new",
        "Launcher Zapret 2.9.1v4": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multisplit --dpi-desync-repeats=2 --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern={4_bin} --new",
        "Launcher Zapret 3.0.0 Extreme mode": "--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls={tlsgoogle} --new --filter-tcp=80,443,444-65535 --ipset={russia_youtube_rtmps} --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset={ipset_discord} --ipset-exclude={ipset_dns} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld --new",
        "Не выбирать":""
    },

    "Ipset UDP": {
        "Apex Legends & Rockstar v1": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic={quicgoogle} --new",
        "Rockstar v3": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic={quic_test_00} --new",
        "General-BF 3.2": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-any-protocol=1 --dpi-desync-autottl=2 --dpi-desync-repeats=9 --dpi-desync-fake-unknown-udp={quicgoogle} --dpi-desync-cutoff=n2 --new",
        "Apex Legends & Rockstar v2": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp={quicgoogle} --dpi-desync-cutoff=n2 --new",
        "IPSET Fake x12 N3 (Apex Legends & Battlefield 6)": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=12 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp={quicgoogle} --dpi-desync-cutoff=n3 --new",
        "IPSET Fake x10 N2 (Apex Legends & Battlefield 6)": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=10 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp={quicgoogle} --dpi-desync-cutoff=n2 --new",
        "IPSET Fake x14 N3 (Apex Legends)": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-autottl=2 --dpi-desync-repeats=10 --dpi-desync-any-protocol=1 --dpi-desync-fake-unknown-udp={quicgoogle} --dpi-desync-cutoff=n2 --new",
        "IPSET Fake + Tamper x11": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake,tamper --dpi-desync-any-protocol --dpi-desync-autottl=2 --dpi-desync-repeats=11 --new",
        "IPSET Fake QUIC6 TTL7": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-fake-unknown-udp={quic_6} --dpi-desync-repeats=2 --dpi-desync-cutoff=n4 --dpi-desync-ttl=7 --new",
        "Fake x11 Simple": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-repeats=11 --new",
        "Fake + Tamper x11": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake,tamper --dpi-desync-repeats=11 --dpi-desync-fake-quic={quicgoogle} --new",
        "Rockstar Launcher": "--filter-udp=* --ipset={ipset_all} --ipset={ipset_base} --ipset={ipset_all2} --ipset={cloudflare_ipset} --ipset={ipset_cloudflare1} --ipset={ipset_cloudflare} --ipset-exclude={ipset_dns} --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic={quicgoogle} --new",
        "Не выбирать":""
    }
}


def get_strategies_names_path():
    """Возвращает путь к файлу с наименованиями выбранных стратегий"""
    manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
    utils_dir = os.path.join(manager_dir, "utils")
    if not os.path.exists(utils_dir):
        os.makedirs(utils_dir)
    return os.path.join(utils_dir, "chosen_strategies.txt")

def save_strategy_names(selected_strategies):
    """Сохраняет наименования выбранных стратегий в файл chosen_strategies.txt и команды в config.txt"""
    try:
        names_path = get_strategies_names_path()
        print(f"Сохраняем в файл: {names_path}")
        print(f"Данные: {selected_strategies}")

        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")
        config_path = os.path.join(manager_dir, "config.txt")

        # Определяем, есть ли валидные стратегии (не "Не выбирать")
        has_valid_strategies = False
        valid_strategies = {}

        for category, strategy_name in selected_strategies.items():
            # Если выбрано "Не выбирать" - пропускаем эту категорию
            if strategy_name == "Не выбирать":
                continue
            has_valid_strategies = True
            valid_strategies[category] = strategy_name

        # Сохраняем наименования в отдельный файл
        with open(names_path, 'w', encoding='utf-8') as f:
            if has_valid_strategies:
                for category, strategy_name in valid_strategies.items():
                    f.write(f"{category}: {strategy_name}\n")
            else:
                # Если нет валидных стратегий, оставляем файл пустым
                f.write("")

        # Записываем имя стратегии в name_strategies.txt
        with open(name_strategy_file, 'w', encoding='utf-8') as f:
            if has_valid_strategies:
                f.write("Custom Strategy")
            else:
                # Если нет валидных стратегий, оставляем файл пустым
                f.write("")

        # Сохраняем команды в config.txt
        with open(config_path, 'w', encoding='utf-8') as f:
            if has_valid_strategies:
                # Добавляем команды выбранных стратегий
                for category, strategy_name in valid_strategies.items():
                    command = get_strategy_command(category, strategy_name)
                    if command:
                        f.write(f"{command}\n")
            else:
                # Если нет валидных стратегий, оставляем config.txt пустым
                f.write("")

        return True
    except Exception as e:
        print(f"Ошибка сохранения стратегий: {e}")
        return False

def load_strategy_names():
    """Загружает наименования выбранных стратегий из файла"""
    try:
        names_path = get_strategies_names_path()
        if not os.path.exists(names_path):
            return {}

        selected_strategies = {}
        with open(names_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    category, strategy_name = line.split(':', 1)
                    category = category.strip()
                    strategy_name = strategy_name.strip()

                    # Проверяем, что это не пустое значение и не "Не выбирать"
                    if strategy_name and strategy_name != "Не выбирать":
                        selected_strategies[category] = strategy_name
                    else:
                        # Если "Не выбирать", устанавливаем пустую строку для этой категории
                        selected_strategies[category] = ""

        return selected_strategies
    except Exception as e:
        print(f"Ошибка загрузки наименований стратегий: {e}")
        return {}

def get_strategy_command(category, strategy_name):
    """Возвращает команду для выбранной стратегии"""
    try:
        return STRATEGY_OPTIONS.get(category, {}).get(strategy_name, "")
    except Exception as e:
        print(f"Ошибка получения команды стратегии: {e}")
        return ""

def clear_empty_strategies():
    """Очищает файлы стратегий если config.txt пустой"""
    try:
        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")
        config_file = os.path.join(manager_dir, "config.txt")
        chosen_strategies_file = get_strategies_names_path()

        # Проверяем config.txt
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:  # Если config.txt пустой
                # Очищаем name_strategy.txt
                if os.path.exists(name_strategy_file):
                    with open(name_strategy_file, 'w', encoding='utf-8') as f:
                        f.write("")

                # Очищаем chosen_strategies.txt
                if os.path.exists(chosen_strategies_file):
                    with open(chosen_strategies_file, 'w', encoding='utf-8') as f:
                        f.write("")

                return True

        return False
    except Exception as e:
        print(f"Ошибка очистки пустых стратегий: {e}")
        return False
