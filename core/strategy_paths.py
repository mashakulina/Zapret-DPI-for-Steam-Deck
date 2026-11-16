"""Shared Flowseal path aliases used by runtime import and resource syncing."""

LISTS = {
    'list-general.txt': 'list_general',
    'list-general-user.txt': 'list_general_user',
    'list-google.txt': 'list_google',
    'list-exclude.txt': 'list_exclude',
    'list-exclude-user.txt': 'list_exclude_user',
    'ipset-all.txt': 'ipset_all',
    'ipset-exclude.txt': 'ipset_exclude',
    'ipset-exclude-user.txt': 'ipset_exclude_user',
}

LEGACY = {
    'quic_initial_www_google_com': 'quicgoogle',
    'tls_clienthello_www_google_com': 'tlsgoogle',
    'tls_clienthello_4pda_to': 'tls4pda',
    'tls_clienthello_max_ru': 'tlsmax',
    'stun': 'stun',
}
