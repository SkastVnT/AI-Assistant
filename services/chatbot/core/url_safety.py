"""
URL safety helpers for tool paths that fetch user-supplied URLs.

Used by tools that accept URLs from chat messages (PDF analyzer, future
document fetchers, etc.). The goal is to block obvious SSRF attempts:

  * non-http(s) schemes (file://, gopher://, ftp://, ldap://, dict://, ...)
  * loopback addresses (127.0.0.0/8, ::1)
  * RFC1918 private ranges (10/8, 172.16/12, 192.168/16)
  * link-local addresses including the cloud metadata endpoint
    169.254.169.254 (AWS/GCP/Azure IMDS)
  * IPv6 unique-local fc00::/7 and IPv4-mapped variants of the above
  * bare hostnames that resolve to those ranges
  * cloud metadata hostnames (metadata.google.internal, etc.)

This is intentionally a *block* list of dangerous targets, not an
allow list. It is defense-in-depth, not a complete sandbox — a fully
trustworthy fetch path would use a separate egress proxy.

Pure stdlib so it works inside venv-core without new dependencies.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Iterable
from urllib.parse import urlsplit

# Hostnames that resolve to internal infrastructure on every major cloud.
# Lower-case match. We compare the host portion case-insensitively.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset({
    "localhost",
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
    "metadata.azure.com",
    "instance-data",
    "instance-data.ec2.internal",
})

# Hostnames that obviously mean loopback even before DNS.
_LOOPBACK_HOSTNAMES: frozenset[str] = frozenset({
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
})

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


class UnsafeUrlError(ValueError):
    """Raised when a URL is rejected as unsafe to fetch."""


def _is_dangerous_ip(addr: ipaddress._BaseAddress) -> bool:
    """Return True for IP addresses we refuse to let server-side code fetch.

    Covers loopback, link-local (incl. AWS/GCP IMDS 169.254.169.254),
    RFC1918, multicast, reserved, and unspecified addresses. Also handles
    IPv4-mapped IPv6 forms by unwrapping them.
    """
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_private
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve_all(host: str) -> Iterable[ipaddress._BaseAddress]:
    """Resolve *host* to all addresses; yields parsed ipaddress objects.

    Uses getaddrinfo so both IPv4 and IPv6 results are inspected. Caller
    must be ready to receive zero items if resolution fails — that itself
    is an unsafe condition (we cannot prove the target is external).
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return ()
    addrs: list[ipaddress._BaseAddress] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            addrs.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue
    return addrs


def is_safe_external_url(url: str, *, resolve: bool = True) -> bool:
    """Cheap boolean wrapper around :func:`assert_safe_external_url`.

    Returns False on *any* validation failure or DNS resolution failure.
    """
    try:
        assert_safe_external_url(url, resolve=resolve)
    except UnsafeUrlError:
        return False
    return True


def assert_safe_external_url(url: str, *, resolve: bool = True) -> None:
    """Validate that *url* is safe for the server to fetch on behalf of a user.

    Raises :class:`UnsafeUrlError` with a short reason on failure.

    Parameters
    ----------
    url:
        The URL to validate. Must already be a string.
    resolve:
        When True (default), perform DNS resolution and reject if any
        resolved address falls in a dangerous range. Set to False only in
        tests where DNS is unavailable.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeUrlError("empty url")
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme {scheme!r} not allowed")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UnsafeUrlError("missing host")
    if host in _LOOPBACK_HOSTNAMES or host in _BLOCKED_HOSTNAMES:
        raise UnsafeUrlError(f"hostname {host!r} blocked")
    # Embedded credentials in the URL are a classic SSRF/phishing trick.
    # If the user-supplied URL needs auth, they should not be sending it
    # through a chat tool.
    if parts.username or parts.password:
        raise UnsafeUrlError("credentials in url not allowed")
    # If host parses directly as an IP literal, check it before DNS.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and _is_dangerous_ip(literal):
        raise UnsafeUrlError(f"ip {host} in blocked range")
    if literal is None and resolve:
        addrs = list(_resolve_all(host))
        if not addrs:
            # Refusing to fetch hosts we cannot resolve is intentional —
            # an attacker can otherwise exploit DNS rebinding tricks or
            # drive the server toward unknown infrastructure.
            raise UnsafeUrlError(f"could not resolve {host!r}")
        for addr in addrs:
            if _is_dangerous_ip(addr):
                raise UnsafeUrlError(f"{host!r} resolved to blocked ip {addr}")
