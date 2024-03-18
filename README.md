<img src="https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

Easily install and manage a multi-protocol, multi-route V2ray VPN server; with user management, domain camouflage (fallback), and route auto update for users.

[Chinese 中文](https://github.com/VZiChoushaDui/Libertea/blob/master/README-zh.md)

[Farsi فارسی](https://github.com/VZiChoushaDui/Libertea/blob/master/README-fa.md)

## Features

- **TROJAN**, **Shadowsocks/v2ray** and **VLESS** protocols (Powered by XRay project)
- **Camouflage domains** with a real website to reduce the risk of being blocked by probing
- **One-command** installation and management
- Support **multiple** domains and IPs, and **auto-select** the best route on user's devices
- **Multi-user management** with connection limitation

## Requirements

- A server running Ubuntu 20.04+ or Debian 11+ (Ubuntu 22.04 recommended)
- At least 1 GB of RAM
- One domain/subdomain pointed to a CDN (such as Cloudflare), and the CDN set to `Full` SSL mode

## Recommended configuration

- Two domains behind a CDN (such as Cloudflare), one for the panel/update and one for the VPN itself
- One or more extra servers for the secondary proxy (512MB RAM is enough for secondary proxies)

## Installation

1. Buy a domain and point its DNS to a CDN (such as Cloudflare), and set the CDN to `Full` SSL mode. [help](https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/cloudflare-full-ssl.png)

2. Set your server's IP address to the CDN's DNS record, and make sure CDN is enabled. (Orange cloud icon in Cloudflare)

3. run the following command on your server and follow the instructions.

       curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *The installation may take a few minutes.*

## Update

To update, just run the following command on your server:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

## Uninstall

If you want to uninstall Liberta or Liberta-secondary-proxy from your server for any reason, run the following command on your server:

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh uninstall

## Contribution

Contributions are welcome! Please feel free to open an issue for any bugs, improvements and ideas; or open a pull request if you want to contribute code. If you're opening a pull request, make sure to send it to the `development` branch of this repository.

## Frequently Asked Questions

### Does Libertea keep my domains and IPs safe from being blocked?

Libertea uses SSL-based protocols, so the traffic is not distinguishable from normal HTTPS traffic. Also by setting a Camouflage domain to your Libertea installation, the risk of active probing gets reduced. However, GFW may still block your domains and IPs based on usage after a period of time. It is recommended to use *multiple* domains and secondary proxies, and periodically change your secondary proxy IPs.

### Can I route regional traffic directly (without going through VPN)?

Yes. In the admin panel, go to the *Settings* tab, and in the *Route regional IPs directly* section, select the countries you want to go through directly.

### Some of my servers or CDN plans have limited traffic. Can I prioritize servers?

Yes. You can set a priority for each domain and secondary proxy; users' devices will try higher priority routes first, and use the lower priority ones only if those are not available. This way, you can optimize your traffic usage per server/domain according to your needs.

### How can I backup my Libertea installation, or move it to another server?

To create a backup from your Libertea, just copy the whole folder `/root/libertea`.

For example, to move Libertea to your new server, run the following commands on your *first* server to copy the Libertea folder to your new server:

    # Run this on your first server
    rsync -avz /root/libertea [new-server-ip]:/root/

When you want to restore it on another server, after copying the folder, just run the Libertea update command on the *new* server:

    # Run this on your new server
    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

### I want to have my own website on the same server running on port 80/443. Can I still use Libertea?

Libertea uses port 80 and 443 for its own purposes and needs to listen to ports 80/443, but you can configure Libertea as a *reverse proxy* for your website or services. To do this, configure your website/services on http on a different port (e.g. `8080`), and then go to the *Settings* tab in the Libertea admin panel, and set `127.0.0.1:8080` as the Camouflage domain. This way, Libertea will forward all requests to your website.

### Can I use Libertea with a custom reverse proxy?

Libertea's HAProxy needs to be the process listening to ports 80 and 443. If you want more customization (than the one available in the question above), you can use Libertea's HAProxy as your reverse proxy by modifying Libertea's HAProxy configuration located at `/root/libertea/haproxy/haproxy.cfg` and then run the following command to apply the changes:

    docker restart libertea-haproxy

You can check the HAProxy logs to see if the changes are applied correctly:

    docker logs -f --tail=100 libertea-haproxy

### Can I use the beta version of Libertea?

Yes, you can use the beta version of Libertea by running the following command on your server:

    export LIBERTEA_BRANCH=beta && curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

Please note that the beta version may have bugs and issues, and it not guaranteed to be stable.

## Changelog

#### v1041

- ✨ Improve camouflage mechanism
- ✨ Added support for custom reverse proxy (see FAQ) 

#### v1040

- ✨ Added domain support for secondary proxies
- ✨ Updated panel icons
- 🐛 Fixed secondary proxy re-adding after removal

#### v1039

- 🚨 New Camouflage mechanism to avoid being blocked
- ⚡️ CPU usage optimization
- 🐛 More reliable Secondary Proxy initial setup
- 🐛 Updated Clash links for Android and Windows
- 🐛 Fixed install fail on Ubuntu 20.04
