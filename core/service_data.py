import os

SERVICE_CATEGORIES = {
    "chatgpt": {
        "chatgpt.com": "138.124.72.139",
        "ab.chatgpt.com": "138.124.72.139",
        "auth.openai.com": "138.124.72.139",
        "auth0.openai.com": "138.124.72.139",
        "platform.openai.com": "138.124.72.139",
        "cdn.oaistatic.com": "138.124.72.139",
        "files.oaiusercontent.com": "138.124.72.139",
        "cdn.auth0.com": "138.124.72.139",
        "tcr9i.chat.openai.com": "138.124.72.139",
        "webrtc.chatgpt.com": "138.124.72.139",
        "android.chat.openai.com": "138.124.72.139",
        "api.openai.com": "138.124.72.139",
        "sora.com": "138.124.72.139",
        "sora.chatgpt.com": "138.124.72.139",
        "videos.openai.com": "138.124.72.139",
        "us.posthog.com": "138.124.72.139",
    },
    "gemini": {
        "gemini.google.com": "138.124.72.139",
        "aistudio.google.com": "138.124.72.139",
        "generativelanguage.googleapis.com": "138.124.72.139",
        "alkalimakersuite-pa.clients6.google.com": "138.124.72.139",
        "aisandbox-pa.googleapis.com": "138.124.72.139",
        "webchannel-alkalimakersuite-pa.clients6.google.com": "138.124.72.139",
        "proactivebackend-pa.googleapis.com": "138.124.72.139",
        "o.pki.goog": "138.124.72.139",
        "labs.google": "138.124.72.139",
        "notebooklm.google": "138.124.72.139",
        "notebooklm.google.com": "138.124.72.139",
    },
    "claude": {
        "claude.ai": "138.124.72.139",
        "api.claude.ai": "138.124.72.139",
        "anthropic.com": "138.124.72.139",
        "www.anthropic.com": "138.124.72.139",
        "api.anthropic.com": "138.124.72.139",
    },
    "copilot": {
        "copilot.microsoft.com": "138.124.72.139",
        "sydney.bing.com": "138.124.72.139",
        "edgeservices.bing.com": "138.124.72.139",
        "rewards.bing.com": "138.124.72.139",
        "xsts.auth.xboxlive.com": "138.124.72.139",
        "www.bing.com": "138.124.72.139",
    },
    "grok": {
        "grok.com": "138.124.72.139",
        "assets.grok.com": "138.124.72.139",
        "accounts.x.ai": "138.124.72.139",
    },
    "instagram": {
        "www.instagram.com": "157.240.225.174",
        "instagram.com": "157.240.225.174",
        "scontent.cdninstagram.com": "157.240.224.63",
        "scontent-hel3-1.cdninstagram.com": "157.240.224.63",
        "static.cdninstagram.com": "31.13.72.53",
        "b.i.instagram.com": "157.240.245.174",
        "threads.com": "157.240.224.63",
        "www.threads.com": "157.240.224.63",
    },
    "facebook": {
        "facebook.com": "31.13.72.36",
        "www.facebook.com": "31.13.72.36",
        "static.xx.fbcdn.net": "31.13.72.12",
        "external-hel3-1.xx.fbcdn.net": "31.13.72.12",
        "scontent-hel3-1.xx.fbcdn.net": "31.13.72.12",
        "z-p42-chat-e2ee-ig.facebook.com": "157.240.245.174",
    },
    "tiktok": {
        "www.tiktok.com": "138.124.72.139",
        "mcs-sg.tiktok.com": "138.124.72.139",
        "mon.tiktokv.com": "138.124.72.139",
    },
    "spotify": {
        "api.spotify.com": "138.124.72.139",
        "xpui.app.spotify.com": "138.124.72.139",
        "appresolve.spotify.com": "138.124.72.139",
        "login5.spotify.com": "138.124.72.139",
        "gew1-spclient.spotify.com": "138.124.72.139",
        "gew1-dealer.spotify.com": "138.124.72.139",
        "spclient.wg.spotify.com": "138.124.72.139",
        "api-partner.spotify.com": "138.124.72.139",
        "aet.spotify.com": "138.124.72.139",
        "www.spotify.com": "138.124.72.139",
        "accounts.spotify.com": "138.124.72.139",
        "spotifycdn.com": "138.124.72.139",
        "open-exp.spotifycdn.com": "138.124.72.139",
        "www-growth.scdn.co": "138.124.72.139",
        "login.app.spotify.com": "138.124.72.139",
        "accounts.scdn.co": "138.124.72.139",
        "ap-gew1.spotify.com": "138.124.72.139",
    },
    "rutracker": {
        "rutracker.org": "172.67.182.196",
        "static.rutracker.cc": "104.21.50.150",
    },
    "rutor": {
        "rutor.info": "172.64.33.155",
        "d.rutor.info": "172.64.33.155",
        "rutor.is": "173.245.59.155",
        "rutor.org": "0.0.0.0",
    },
    "notion": {
        "www.notion.so": "138.124.72.139",
        "notion.so": "138.124.72.139",
        "calendar.notion.so": "138.124.72.139",
    },
    "soundcloud": {
        "soundcloud.com": "18.238.243.27",
        "style.sndcdn.com": "13.224.222.71",
        "a-v2.sndcdn.com": "3.164.206.34",
        "secure.sndcdn.com": "18.165.140.56",
    },
    "twitch": {
        "usher.ttvnw.net": "138.124.72.139",
        "gql.twitch.tv": "138.124.72.139",
    },
    "other": {
        "www.aomeitech.com": "0.0.0.0",
        "www.intel.com": "138.124.72.139",
        "www.dell.com": "138.124.72.139",
        "developer.nvidia.com": "138.124.72.139",
        "truthsocial.com": "204.12.192.221",
        "static-assets-1.truthsocial.com": "204.12.192.221",
        "autodesk.com": "94.131.119.85",
        "accounts.autodesk.com": "94.131.119.85",
        "www.hulu.com": "2.19.183.66",
        "hulu.com": "2.22.31.233",
        "anilib.me": "172.67.192.246",
        "ntc.party": "130.255.77.28",
        "pump.fun": "138.124.72.139",
        "frontend-api-v3.pump.fun": "138.124.72.139",
        "images.pump.fun": "138.124.72.139",
        "swap-api.pump.fun": "138.124.72.139",
        "www.elgato.com": "138.124.72.139",
        "info.dns.malw.link": "104.21.24.110",
        "protonmail.com": "3.66.189.153",
        "mail.proton.me": "3.66.189.153",
        "codeium.com": "50.7.87.85",
        "inference.codeium.com": "50.7.85.219",
        "api.individual.githubcopilot.com": "89.108.98.20",
        "proxy.individual.githubcopilot.com": "89.108.98.20",
        "datalore.jetbrains.com": "50.7.85.221",
        "plugins.jetbrains.com": "107.150.34.100",
        "elevenlabs.io": "204.12.192.222",
        "api.us.elevenlabs.io": "204.12.192.222",
        "elevenreader.io": "204.12.192.222",
        "aitestkitchen.withgoogle.com": "204.12.192.222",
        "encore.scdn.co": "138.201.204.218",
        "www.netflix.com": "158.255.0.189",
        "netflix.com": "158.255.0.189",
        "deepl.com": "204.12.192.222",
        "www.deepl.com": "204.12.192.222",
        "s.deepl.com": "204.12.192.222",
        "ita-free.www.deepl.com": "204.12.192.222",
        "experimentation.deepl.com": "204.12.192.222",
        "w.deepl.com": "204.12.192.222",
        "login-wall.deepl.com": "204.12.192.222",
        "gtm.deepl.com": "204.12.192.222",
        "checkout.www.deepl.com": "204.12.192.222",
    }
}

# Для обратной совместимости: объединенный словарь всех доменов
PROXY_DOMAINS = {}
for category in SERVICE_CATEGORIES.values():
    PROXY_DOMAINS.update(category)

# Функции для удобного доступа к данным
def get_category_domains(category_name):
    """Получить домены определенной категории"""
    return SERVICE_CATEGORIES.get(category_name, {})

def get_all_categories():
    """Получить список всех доступных категорий"""
    return list(SERVICE_CATEGORIES.keys())

def get_domain_ip(domain):
    """Получить IP для конкретного домена"""
    return PROXY_DOMAINS.get(domain)

def get_categories_for_domain(domain):
    """Получить категории, к которым принадлежит домен"""
    categories = []
    for cat_name, cat_domains in SERVICE_CATEGORIES.items():
        if domain in cat_domains:
            categories.append(cat_name)
    return categories
