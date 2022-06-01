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

1. Buy a domain and set its DNS to a CDN (such as Cloudflare)

2. Set SSL encryption to `Full` in the SSL settings. [help](https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/cloudflare-full-ssl.png)

3. Buy a server running Ubuntu (22.04 is preferred) and route your domain from CDN panel to its IP

4. run the following command on your server:

        curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *The installation may take a few minutes.*

5. Provide the domain name and a password for the panel when prompted.

6. Visit the link provided by the script to access the panel.

## Update

To update, just run the following command on your server:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update
