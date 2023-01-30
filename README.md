<img src="https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

Easily install and manage a Clash VPN server; with user management, auto fallback and auto update.

## Features

- One-command installation and management
- Auto select the best route on user's devices
- TROJAN, Shadowsocks/v2ray and VLESS protocols
- User management
- Support multiple domains behind CDN
- Secondary IPs for better availability

## Requirements

- At least one server with Ubuntu 20.04+ or Debian 11+ (Ubuntu 22.04 recommended)
- At least one domain behind a CDN (such as Cloudflare)


## Recommended configuration

- Two domains behind a CDN (such as Cloudflare), one for the panel/update and one for the VPN itself
- An extra server for the secondary proxy

## Installation

1. Buy a domain and point its DNS to a CDN (such as Cloudflare), and set the CDN to `Full` SSL mode. [help](https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/cloudflare-full-ssl.png)

2. Set your server's IP address to the CDN's DNS record, and make sure CDN is enabled. (Orange cloud icon in Cloudflare)

3. run the following command on your server and follow the instructions.

        curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *The installation may take a few minutes.*

## Update

To update, just run the following command on your server:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

## Frequently Asked Questions

##### Does Libertea keep my domains and IPs safe from being blocked?

No, Libertea uses SSL-based protocols, so the traffic is not distinguishable from normal HTTPS traffic. However, GFW may still block your domains and IPs based on usage after a period of time. It is recommended to use *multiple* domains and secondary proxies, and periodically change your secondary proxy IPs.

##### Can I route regional traffic directly (without going through VPN)?

Yes. In the admin panel, go to the *Settings* tab, and in the *Route regional IPs directly* section, select the countries you want to go through directly.
