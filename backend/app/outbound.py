"""Explicitly approved endpoints for city feeds and notification connectors."""

import ipaddress
import os
import socket
from urllib.parse import urlsplit

import httpx


class EndpointError(ValueError):
    pass


def resolve(url, variable, schemes):
    try:
        parsed = urlsplit(url)
        host, port = parsed.hostname, parsed.port
        if (
            not host
            or parsed.scheme not in schemes
            or parsed.username
            or parsed.password
            or parsed.fragment
            or "\\" in url
            or any(char.isspace() for char in url)
        ):
            raise ValueError
    except ValueError as exc:
        raise EndpointError("Use an approved endpoint without URL credentials.") from exc
    allowed = {item.strip().rstrip("/") for item in os.getenv(variable, "").split(",") if item.strip()}
    insecure = {"http", "ws", "mqtt"}
    origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
    if origin not in allowed:
        raise EndpointError(f"Approve the endpoint origin in {variable}.")
    effective_port = port or (
        1883
        if parsed.scheme == "mqtt"
        else 8883
        if parsed.scheme == "mqtts"
        else 80
        if parsed.scheme in insecure
        else 443
    )
    try:
        addresses = [
            ipaddress.ip_address(entry[4][0])
            for entry in socket.getaddrinfo(host, effective_port, type=socket.SOCK_STREAM)
        ]
    except OSError as exc:
        raise EndpointError("The endpoint could not be resolved.") from exc
    if not addresses or any(
        entry.is_link_local
        or entry.is_multicast
        or entry.is_unspecified
        or entry == ipaddress.ip_address("169.254.169.254")
        for entry in addresses
    ):
        raise EndpointError("The endpoint resolved to an unsupported network address.")
    address = next((value for value in addresses if value.version == 4), addresses[0])
    return parsed, str(address), effective_port


def request_bytes(method, url, variable, *, headers=None, body=None, limit=1_000_000, timeout=8):
    parsed, address, _ = resolve(url, variable, {"http", "https"})
    extensions = {"sni_hostname": parsed.hostname} if parsed.scheme == "https" else {}
    target = httpx.URL(url).copy_with(host=address)
    with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=False) as client:
        with client.stream(
            method, target, headers={**(headers or {}), "Host": parsed.netloc}, json=body, extensions=extensions
        ) as response:
            if not response.is_success:
                raise EndpointError(f"Endpoint returned HTTP {response.status_code}.")
            chunks = bytearray()
            for part in response.iter_bytes():
                chunks.extend(part)
                if len(chunks) > limit:
                    raise EndpointError("The endpoint response exceeded the size limit.")
            return bytes(chunks)
