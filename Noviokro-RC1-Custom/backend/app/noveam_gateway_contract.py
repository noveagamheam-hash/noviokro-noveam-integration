"""NOVEAM-only gateway contract shared by transport and isolated tests."""
import ipaddress
from urllib.parse import urlsplit

HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
               'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-length',
               'host', 'x-admin-key', 'cookie', 'set-cookie', 'forwarded',
               'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto'}


def backend_origin(value):
    parsed = urlsplit(value)
    port = parsed.port  # Validate malformed/out-of-range ports before transport.
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/')):
        raise ValueError('Configure a NOVEAM HTTP(S) origin without credentials or a path')
    try:
        local = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = parsed.hostname == 'localhost'
    if parsed.scheme == 'http' and not local:
        raise ValueError('Non-loopback NOVEAM backends require HTTPS')
    if local and parsed.port in (3000, 8002):
        raise ValueError('NOVEAM backend must not point back to the manager')
    return value.rstrip('/')


def api_path(path):
    full = '/api/' + path
    if ('%' in path or '\\' in path or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or any(part in ('.', '..', '') for part in path.split('/'))):
        raise ValueError('Invalid NOVEAM API path')
    return full


def forwarded_headers(items, response=False):
    items = list(items)
    excluded = set(HOP_HEADERS)
    for name, value in items:
        if name.lower() == 'connection':
            excluded.update(part.strip().lower() for part in value.split(','))
    if response:
        excluded.update({'content-encoding', 'location', 'access-control-allow-origin',
                         'access-control-allow-credentials', 'access-control-expose-headers'})
    return {name: value for name, value in items if name.lower() not in excluded}
