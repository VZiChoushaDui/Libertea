<img src="https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

Easily install and manage a Clash VPN server; with auto fallback, auto update and user management. 

## Features

- One-command installation and management
- Auto select the best route on user's devices
- TROJAN and VLESS protocols
- User management
- Support multiple domains behind CDN
- Secondary IPs for better availability

## Requirements

- At least one server with Ubuntu 20.04 or higher (Ubuntu 22.04 recommended)
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
