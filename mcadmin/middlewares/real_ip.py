from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network
from aiohttp import web
from typing import Union
from mcadmin.utils.web import get_di

__all__ = ["real_ip_middleware"]


@web.middleware
async def real_ip_middleware(request, handler):
    req_chain = request.headers.get("X-Forwarded-For", "")
    trusted_proxies: list[Union[IPv4Address, IPv6Address, IPv4Network, IPv6Network]] = get_di(request).web_server_config["trusted_proxies"]
    remote = request.remote

    if not req_chain or not trusted_proxies:
        request["real_ip"] = remote
        return await handler(request)

    ip_list = [ip.strip() for ip in req_chain.split(",") if ip.strip()]
    if remote:
        ip_list.append(remote)

    client_ip = None

    for candidate in reversed(ip_list):
        try:
            candidate_ip = ip_address(candidate)
        except ValueError:
            continue

        if any((isinstance(proxy, (IPv4Network, IPv6Network)) and candidate_ip in proxy) or (isinstance(proxy, (IPv4Address, IPv6Address)) and candidate_ip == proxy) for proxy in trusted_proxies):
            continue

        client_ip = candidate
        break

    if client_ip is None:
        client_ip = remote

    request["real_ip"] = client_ip

    return await handler(request)
