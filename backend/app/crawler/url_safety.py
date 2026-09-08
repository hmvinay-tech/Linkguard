import ipaddress
import socket
from urllib.parse import urlparse


PRIVATE_HOSTNAMES = {"localhost", "localhost.localdomain"}
ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrlError(ValueError):
    pass


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("Only http and https URLs are supported.")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname.")

    host = parsed.hostname.lower()
    if host in PRIVATE_HOSTNAMES or host.endswith(".localhost"):
        raise UnsafeUrlError("Localhost URLs are not allowed.")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        _validate_resolved_addresses(host)
    else:
        _validate_ip(ip)


def _validate_resolved_addresses(host: str) -> None:
    try:
        results = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return

    for result in results:
        address = result[4][0]
        _validate_ip(ipaddress.ip_address(address))


def _validate_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise UnsafeUrlError("Private, local, reserved, and metadata IPs are not allowed.")
