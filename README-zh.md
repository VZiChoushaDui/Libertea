<img src="https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/logo-complete.png" style="width: 300px" />

# Libertea

轻松安装和管理多协议、多路由的 V2ray VPN 服务器；具有用户管理、域伪装和自动更新功能。

[English](https://github.com/VZiChoushaDui/Libertea/blob/master/README.md)

[波斯语 فارسی](https://github.com/VZiChoushaDui/Libertea/blob/master/README-fa.md)

## 特征

- **TROJAN**、**Shadowsocks/v2ray** 和 **VLESS** 协议（由 XRay 项目提供支持）
- **伪装域名** 带有真实网站以降低被探测阻止的风险
- **一个命令**安装和管理
- 支持**多个**域和IP，并**自动选择**用户设备上的最佳路由
- **多用户管理**有连接限制

## 要求

- 运行 Ubuntu 20.04+ 或 Debian 11+ 的服务器（推荐 Ubuntu 22.04）
- 至少 1 GB 的内存
- 一个域/子域指向一个 CDN（例如 Cloudflare），并且 CDN 设置为“Full”SSL 模式

## 推荐配置

- CDN 后面的两个域（例如 Cloudflare），一个用于面板/更新，一个用于 VPN 本身
- 用于辅助代理的一台或多台额外服务器（512MB RAM 足以用于辅助代理）

## 安装

1. 购买一个域并将其 DNS 指向 CDN（例如 Cloudflare），并将 CDN 设置为 `Full` SSL 模式。 [帮助](https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/docs/cloudflare-full-ssl.png)

2. 将服务器的IP地址设置为CDN的DNS记录，并确保CDN已启用。 （Cloudflare 中的橙色云图标）

3. 在您的服务器上运行以下命令并按照说明进行操作。

       curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh install

    *安装可能需要几分钟。*

## 更新

要更新，只需在您的服务器上运行以下命令：

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh update

## 卸载

如果您出于任何原因想要从您的服务器卸载 Liberta 或 Liberta-secondary-proxy，请在您的服务器上运行以下命令：

    curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh -o /tmp/bootstrap.sh && bash /tmp/bootstrap.sh uninstall

## 贡献

欢迎投稿！请随时为任何错误、改进和想法打开一个问题；或者如果您想贡献代码，请打开拉取请求。如果您打开拉取请求，请确保将其发送到此存储库的“开发”分支。

## 经常问的问题

##### Libertea 是否保护我的域和 IP 不被阻止？

Libertea 使用基于 SSL 的协议，因此流量与正常的 HTTPS 流量无法区分。此外，通过为您的 Libertea 安装设置伪装域，可以降低主动探测的风险。但是，GFW 可能会在一段时间后根据使用情况阻止您的域和 IP。建议使用*多个*域和二级代理，并定期更改您的二级代理 IP。

##### 我可以直接路由区域流量（不通过 VPN）吗？

是的。在管理面板中，转到*设置*选项卡，然后在*直接路由区域 IP* 部分中，选择您要直接经过的国家/地区。

##### 我的一些服务器或 CDN 计划流量有限。我可以优先考虑服务器吗？

是的。您可以为每个域和二级代理设置优先级；用户的设备将首先尝试优先级较高的路由，只有在这些路由不可用时才使用优先级较低的路由。这样，您就可以根据需要优化每个服务器/域的流量使用。
